from datetime import datetime, timezone

import pytest

from sentineltrade.config import Settings, validate_settings
from sentineltrade.domain import OrderStatus, ALLOWED_TRANSITIONS, is_trading_window
from sentineltrade.security import hash_secret, verify_secret, create_token, read_token


def test_order_state_machine_accepts_valid_transition():
    assert OrderStatus.VALIDATED in ALLOWED_TRANSITIONS[OrderStatus.CREATED]
    assert OrderStatus.SENT in ALLOWED_TRANSITIONS[OrderStatus.VALIDATED]
    assert OrderStatus.FILLED in ALLOWED_TRANSITIONS[OrderStatus.PARTIALLY_FILLED]


def test_order_state_machine_allows_successive_partial_fills():
    assert OrderStatus.PARTIALLY_FILLED in ALLOWED_TRANSITIONS[OrderStatus.PARTIALLY_FILLED]


def test_order_state_machine_blocks_reopening_final_state():
    assert ALLOWED_TRANSITIONS[OrderStatus.FILLED] == set()
    assert ALLOWED_TRANSITIONS[OrderStatus.REJECTED] == set()
    assert ALLOWED_TRANSITIONS[OrderStatus.CANCELLED] == set()


def test_password_and_pin_hashing():
    encoded = hash_secret("senha-segura")
    assert encoded != "senha-segura"
    assert verify_secret("senha-segura", encoded)
    assert not verify_secret("senha-errada", encoded)


def test_signed_token():
    token = create_token(12, "INVESTOR")
    assert read_token(token)["id"] == 12
    assert read_token(token)["role"] == "INVESTOR"
    assert read_token("token-invalido") is None


def test_tampered_token_is_rejected():
    user_id, role, expiry, signature = create_token(12, "INVESTOR").split(":")
    assert read_token(f"{user_id}:ADMIN:{expiry}:{signature}") is None


# 2026-11-24 é terça-feira; America/Sao_Paulo = UTC-3 (sem horário de verão).
@pytest.mark.parametrize("moment, expected", [
    (datetime(2026, 11, 24, 12, 59, tzinfo=timezone.utc), False),      # 09:59
    (datetime(2026, 11, 24, 13, 0, tzinfo=timezone.utc), True),        # 10:00
    (datetime(2026, 11, 24, 20, 55, tzinfo=timezone.utc), True),       # 17:55
    (datetime(2026, 11, 24, 20, 55, 30, tzinfo=timezone.utc), True),   # 17:55:30 ainda é o minuto 17:55
    (datetime(2026, 11, 24, 20, 56, tzinfo=timezone.utc), False),      # 17:56
    (datetime(2026, 11, 28, 15, 0, tzinfo=timezone.utc), False),       # sábado
    (datetime(2026, 11, 29, 15, 0, tzinfo=timezone.utc), False),       # domingo
])
def test_trading_window(moment, expected):
    assert is_trading_window(moment) is expected


def test_production_rejects_weak_secret():
    with pytest.raises(RuntimeError):
        validate_settings(Settings(app_env="production", secret_key="curta"))
    with pytest.raises(RuntimeError):
        validate_settings(Settings(app_env="production", secret_key="change-this-to-a-long-random-secret"))


def test_production_accepts_strong_secret_and_development_is_lenient():
    validate_settings(Settings(app_env="production", secret_key="x" * 40))
    validate_settings(Settings(app_env="development", secret_key="dev-only-change-this-secret"))
