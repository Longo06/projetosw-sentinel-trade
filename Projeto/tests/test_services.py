from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from sentineltrade import services
from sentineltrade.domain import OrderStatus, OrderType, Side
from sentineltrade.integrations import SimulatedQuoteProvider
from sentineltrade.models import Asset, Position, TradeOrder
from sentineltrade.services import BusinessError, change_status

from conftest import PASSWORD, PIN, order_data


# ---------- máquina de estados ----------

class FakeOrder:
    id = 1
    investor_id = 1
    status = "FILLED"


def test_final_order_cannot_be_cancelled_or_reopened():
    order = FakeOrder()

    class FakeDB:
        def add(self, value):
            pass

    with pytest.raises(BusinessError):
        change_status(FakeDB(), order, OrderStatus.CANCELLED, "")
    assert order.status == "FILLED"


# ---------- cotação simulada ----------

def test_simulated_quote_is_fresh_by_default_even_with_old_persisted_timestamp():
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    asset = Asset(symbol="X1", name="X", last_price=Decimal("10"), quote_at=old)
    quote = SimulatedQuoteProvider().get_quote(asset)
    assert abs((datetime.now(timezone.utc) - quote.timestamp).total_seconds()) < 5


def test_simulated_quote_can_simulate_stale_data():
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    asset = Asset(symbol="X1", name="X", last_price=Decimal("10"), quote_at=old)
    assert SimulatedQuoteProvider(fresh=False).get_quote(asset).timestamp == old


# ---------- autenticação ----------

def test_login_and_mfa_success(db, investor):
    _, challenge, code = services.login_start(db, investor.email, PASSWORD)
    assert code is not None and len(code) == 6
    assert services.verify_mfa(db, challenge.id, code).id == investor.id


def test_mfa_code_cannot_be_reused(db, investor):
    _, challenge, code = services.login_start(db, investor.email, PASSWORD)
    services.verify_mfa(db, challenge.id, code)
    with pytest.raises(BusinessError):
        services.verify_mfa(db, challenge.id, code)


def test_new_login_invalidates_previous_challenge(db, investor):
    _, first, first_code = services.login_start(db, investor.email, PASSWORD)
    services.login_start(db, investor.email, PASSWORD)
    with pytest.raises(BusinessError):
        services.verify_mfa(db, first.id, first_code)


def test_three_wrong_passwords_block_account(db, investor):
    for _ in range(3):
        with pytest.raises(BusinessError, match="inválidas"):
            services.login_start(db, investor.email, "senha-errada")
    with pytest.raises(BusinessError, match="bloqueada"):
        services.login_start(db, investor.email, PASSWORD)


def test_unknown_email_gets_generic_error(db):
    with pytest.raises(BusinessError, match="inválidas"):
        services.login_start(db, "ninguem@teste.local", PASSWORD)


def test_blocked_account_cannot_finish_mfa(db, investor):
    _, challenge, code = services.login_start(db, investor.email, PASSWORD)
    for _ in range(3):
        with pytest.raises(BusinessError):
            services.verify_mfa(db, challenge.id, "000000" if code != "000000" else "111111")
    with pytest.raises(BusinessError):
        services.verify_mfa(db, challenge.id, code)


def test_relogin_does_not_reset_failures_so_mfa_guessing_still_blocks(db, investor):
    """RN-12: errar o MFA, logar de novo e repetir não pode zerar o contador de falhas."""
    for _ in range(3):
        _, challenge, code = services.login_start(db, investor.email, PASSWORD)
        wrong = "000000" if code != "000000" else "111111"
        with pytest.raises(BusinessError, match="inválido"):
            services.verify_mfa(db, challenge.id, wrong)
    with pytest.raises(BusinessError, match="bloqueada"):
        services.login_start(db, investor.email, PASSWORD)


def test_successful_mfa_resets_failure_counter(db, investor):
    with pytest.raises(BusinessError):
        services.login_start(db, investor.email, "senha-errada")
    _, challenge, code = services.login_start(db, investor.email, PASSWORD)
    services.verify_mfa(db, challenge.id, code)
    assert investor.failed_attempts == 0


# ---------- envio de ordens ----------

def test_buy_order_reserves_balance_and_is_sent(db, investor, asset, market_open):
    order = services.place_order(db, investor, order_data())
    assert order.status == "SENT"
    assert order.reserved_cash == Decimal("385.00")
    assert investor.balance == Decimal("99615.00")


def test_same_idempotency_key_creates_only_one_order(db, investor, asset, market_open):
    data = order_data()
    first = services.place_order(db, investor, data)
    second = services.place_order(db, investor, data)
    assert first.id == second.id
    assert investor.balance == Decimal("99615.00")
    assert len(db.scalars(select(TradeOrder)).all()) == 1


def test_order_is_accepted_even_when_persisted_quote_is_old(db, investor, asset, market_open):
    asset.quote_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()
    assert services.place_order(db, investor, order_data()).status == "SENT"


def test_stale_quote_is_rejected(db, investor, asset, market_open, monkeypatch):
    monkeypatch.setattr(services.quotes, "fresh", False)
    asset.quote_at = datetime.now(timezone.utc) - timedelta(seconds=60)
    db.commit()
    with pytest.raises(BusinessError, match="desatualizada"):
        services.place_order(db, investor, order_data())
    assert investor.balance == Decimal("100000")


def test_order_outside_trading_hours_is_rejected(db, investor, asset, monkeypatch):
    monkeypatch.setattr("sentineltrade.services.is_trading_window", lambda *args, **kwargs: False)
    with pytest.raises(BusinessError, match="dias úteis"):
        services.place_order(db, investor, order_data())
    assert investor.balance == Decimal("100000")


def test_wrong_pin_is_rejected_and_blocks_after_three_failures(db, investor, asset, market_open):
    for _ in range(3):
        with pytest.raises(BusinessError, match="PIN"):
            services.place_order(db, investor, order_data(pin="9999"))
    with pytest.raises(BusinessError, match="bloqueada"):
        services.place_order(db, investor, order_data(pin=PIN))


def test_correct_pin_resets_consecutive_failures(db, investor, asset, market_open):
    for _ in range(2):
        with pytest.raises(BusinessError, match="PIN"):
            services.place_order(db, investor, order_data(pin="9999"))
    services.place_order(db, investor, order_data())            # PIN correto zera a sequência
    assert investor.failed_attempts == 0
    with pytest.raises(BusinessError, match="PIN"):             # 1ª falha de uma nova sequência
        services.place_order(db, investor, order_data(pin="9999"))
    assert investor.blocked_until is None


def test_market_order_does_not_store_limit_price(db, investor, asset, market_open):
    order = services.place_order(db, investor, order_data(limit_price=Decimal("1.00")))
    assert order.order_type == "MARKET" and order.limit_price is None


def test_limit_order_requires_limit_price(db, investor, asset, market_open):
    with pytest.raises(BusinessError, match="limit_price"):
        services.place_order(db, investor, order_data(order_type=OrderType.LIMIT))


def test_limit_order_reserves_by_limit_price(db, investor, asset, market_open):
    order = services.place_order(db, investor, order_data(order_type=OrderType.LIMIT,
                                                          limit_price=Decimal("30.00")))
    assert order.reserved_cash == Decimal("300.00")


def test_insufficient_balance(db, investor, asset, market_open):
    investor.balance = Decimal("100")
    with pytest.raises(BusinessError, match="Saldo"):
        services.place_order(db, investor, order_data())


def test_order_value_limit(db, investor, asset, market_open):
    investor.daily_order_limit = Decimal("100")
    with pytest.raises(BusinessError, match="limite por ordem"):
        services.place_order(db, investor, order_data())


def test_daily_exposure_limit(db, investor, asset, market_open):
    investor.daily_exposure_limit = Decimal("500")
    services.place_order(db, investor, order_data())          # 385
    with pytest.raises(BusinessError, match="Exposição"):
        services.place_order(db, investor, order_data())      # 385 + 385 > 500


def test_sell_requires_available_position(db, investor, asset, market_open):
    with pytest.raises(BusinessError, match="Posição"):
        services.place_order(db, investor, order_data(side=Side.SELL))


def test_broker_failure_releases_reservation(db, investor, asset, market_open, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("corretora fora do ar")

    monkeypatch.setattr(services.broker, "submit", boom)
    with pytest.raises(BusinessError, match="reserva liberada"):
        services.place_order(db, investor, order_data())
    assert investor.balance == Decimal("100000")
    assert db.scalar(select(TradeOrder)).status == "REJECTED"


# ---------- cancelamento ----------

def test_cancel_returns_reserved_cash(db, investor, asset, market_open):
    order = services.place_order(db, investor, order_data())
    services.cancel_order(db, investor, order)
    assert order.status == "CANCELLED"
    assert investor.balance == Decimal("100000.00")


def test_cannot_cancel_other_investors_order(db, investor, asset, market_open):
    from conftest import make_user
    other = make_user(db, email="outro@teste.local")
    order = services.place_order(db, investor, order_data())
    with pytest.raises(BusinessError):
        services.cancel_order(db, other, order)


def test_cannot_cancel_filled_order(db, investor, asset, market_open):
    order = services.place_order(db, investor, order_data())
    services.apply_broker_update(db, order, OrderStatus.FILLED, 10)
    with pytest.raises(BusinessError):
        services.cancel_order(db, investor, order)


# ---------- retornos da corretora ----------

def test_full_fill_creates_position_and_keeps_balance_debited_once(db, investor, asset, market_open):
    order = services.place_order(db, investor, order_data())
    services.apply_broker_update(db, order, OrderStatus.FILLED, 10)
    db.commit()
    assert order.status == "FILLED"
    assert order.reserved_cash == 0
    assert investor.balance == Decimal("99615.00")
    assert services.portfolio(db, investor.id)["positions"] == [
        {"symbol": "PETR4", "quantity": 10, "reserved_quantity": 0, "available": 10}]


def test_partial_fill_then_cancel_releases_only_the_remaining_cash(db, investor, asset, market_open):
    order = services.place_order(db, investor, order_data())          # reserva 385,00
    services.apply_broker_update(db, order, OrderStatus.PARTIALLY_FILLED, 4)
    assert order.status == "PARTIALLY_FILLED"
    assert order.reserved_cash == Decimal("231.00")                   # 385 - 4 x 38,50
    assert investor.balance == Decimal("99615.00")                    # nenhuma devolução indevida
    services.cancel_order(db, investor, order)
    assert order.status == "CANCELLED"
    assert investor.balance == Decimal("99846.00")                    # gastou só 4 x 38,50 = 154,00


def test_successive_partial_fills_then_full_fill(db, investor, asset, market_open):
    order = services.place_order(db, investor, order_data())
    services.apply_broker_update(db, order, OrderStatus.PARTIALLY_FILLED, 3)
    services.apply_broker_update(db, order, OrderStatus.PARTIALLY_FILLED, 6)
    services.apply_broker_update(db, order, OrderStatus.FILLED, 10)
    assert order.status == "FILLED"
    assert investor.balance == Decimal("99615.00")
    position = db.scalar(select(Position))
    assert position.quantity == 10


def test_filled_requires_full_quantity_and_changes_nothing_on_error(db, investor, asset, market_open):
    order = services.place_order(db, investor, order_data())
    with pytest.raises(BusinessError):
        services.apply_broker_update(db, order, OrderStatus.FILLED, 5)
    assert order.status == "SENT"
    assert order.filled_quantity == 0
    assert db.scalar(select(Position)) is None


def test_partial_fill_must_be_strictly_between_zero_and_total(db, investor, asset, market_open):
    order = services.place_order(db, investor, order_data())
    for invalid in (0, 10, 11):
        with pytest.raises(BusinessError):
            services.apply_broker_update(db, order, OrderStatus.PARTIALLY_FILLED, invalid)


def test_duplicate_broker_update_is_idempotent(db, investor, asset, market_open):
    order = services.place_order(db, investor, order_data())
    services.apply_broker_update(db, order, OrderStatus.PARTIALLY_FILLED, 4)
    services.apply_broker_update(db, order, OrderStatus.PARTIALLY_FILLED, 4)
    assert db.scalar(select(Position)).quantity == 4
    assert order.reserved_cash == Decimal("231.00")


def test_broker_rejection_releases_cash_and_blocks_fill_afterwards(db, investor, asset, market_open):
    order = services.place_order(db, investor, order_data())
    services.apply_broker_update(db, order, OrderStatus.REJECTED, 0, "Recusada pela bolsa simulada")
    assert order.status == "REJECTED"
    assert order.rejection_reason == "Recusada pela bolsa simulada"
    assert investor.balance == Decimal("100000.00")
    with pytest.raises(BusinessError, match="final"):
        services.apply_broker_update(db, order, OrderStatus.FILLED, 10)


def test_sell_flow_reserves_position_and_credits_cash_on_fill(db, investor, asset, market_open):
    db.add(Position(investor_id=investor.id, asset_id=asset.id, quantity=10, reserved_quantity=0))
    db.commit()
    order = services.place_order(db, investor, order_data(side=Side.SELL, quantity=5))
    position = db.scalar(select(Position))
    assert position.reserved_quantity == 5
    with pytest.raises(BusinessError, match="Posição"):               # só restam 5 disponíveis
        services.place_order(db, investor, order_data(side=Side.SELL, quantity=6))
    services.apply_broker_update(db, order, OrderStatus.FILLED, 5)
    assert position.quantity == 5
    assert position.reserved_quantity == 0
    assert investor.balance == Decimal("100192.50")                   # 100000 + 5 x 38,50
