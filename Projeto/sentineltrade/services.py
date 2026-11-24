from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
import secrets
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .models import Investor, Asset, Position, TradeOrder, OrderEvent, AuditEvent, MfaChallenge, Notification
from .domain import Side, OrderType, OrderStatus, CANCELLABLE_STATES, FINAL_STATES, ALLOWED_TRANSITIONS, is_trading_window
from .security import hash_secret, verify_secret
from .integrations import SimulatedQuoteProvider, SimulatedBroker, ConsoleNotificationGateway
from .config import settings

quotes = SimulatedQuoteProvider()
broker = SimulatedBroker()
gateway = ConsoleNotificationGateway()

MAX_FAILED_ATTEMPTS = 3      # RN-12
BLOCK_MINUTES = 15           # RN-12
MFA_MAX_ATTEMPTS = 3
CENT = Decimal("0.01")

class BusinessError(Exception):
    pass

def money(value) -> Decimal:
    """Normaliza valores monetários para centavos (evita resíduos de 4 casas decimais)."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)

def as_utc(moment: datetime) -> datetime:
    """Garante datetime com fuso UTC (SQLite devolve datas sem fuso)."""
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)

def audit(db: Session, event_type: str, investor_id=None, order_id=None, details=""):
    db.add(AuditEvent(investor_id=investor_id, order_id=order_id, event_type=event_type, details=details[:4000]))

def notify(db: Session, investor: Investor, message: str):
    db.add(Notification(investor_id=investor.id, message=message[:500]))
    gateway.send(investor.email, message)

def change_status(db: Session, order: TradeOrder, new_status: OrderStatus, message=""):
    old = OrderStatus(order.status)
    if new_status not in ALLOWED_TRANSITIONS[old]:
        raise BusinessError(f"Transição inválida: {old.value} -> {new_status.value}")
    order.status = new_status.value
    order.updated_at = datetime.now(timezone.utc)
    db.add(OrderEvent(order_id=order.id, old_status=old.value, new_status=new_status.value, message=message[:500]))
    audit(db, "ORDER_STATUS_CHANGED", order.investor_id, order.id, f"{old.value}->{new_status.value}: {message}")

def ensure_not_blocked(user: Investor, now: datetime):
    """RN-12: conta bloqueada não autentica nem opera."""
    if user.blocked_until and as_utc(user.blocked_until) > now:
        raise BusinessError("Conta temporariamente bloqueada.")

def create_investor(db: Session, data):
    email = data.email.lower()
    if db.scalar(select(Investor).where(Investor.email == email)):
        raise BusinessError("E-mail já cadastrado.")
    user = Investor(name=data.name, email=email, password_hash=hash_secret(data.password),
                    pin_hash=hash_secret(data.pin), role="INVESTOR")
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:  # cadastro concorrente com o mesmo e-mail
        db.rollback()
        raise BusinessError("E-mail já cadastrado.") from exc
    audit(db, "INVESTOR_CREATED", user.id, details="Cadastro de investidor")
    return user

_dummy_hash = None

def _burn_hash(password: str):
    """Gasta o mesmo tempo de uma verificação real quando o e-mail não existe (anti-enumeração)."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_secret("senha-descartavel")
    verify_secret(password, _dummy_hash)

def login_start(db: Session, email: str, password: str):
    user = db.scalar(select(Investor).where(Investor.email == email.lower()))
    if not user or not user.active:
        _burn_hash(password)
        raise BusinessError("Credenciais inválidas.")
    now = datetime.now(timezone.utc)
    ensure_not_blocked(user, now)
    if not verify_secret(password, user.password_hash):
        register_failure(db, user, "LOGIN_FAILURE")
        raise BusinessError("Credenciais inválidas.")
    user.failed_attempts = 0
    # Um novo login invalida desafios MFA anteriores ainda pendentes.
    for old in db.scalars(select(MfaChallenge).where(MfaChallenge.investor_id == user.id,
                                                     MfaChallenge.used.is_(False))):
        old.used = True
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = MfaChallenge(investor_id=user.id, code_hash=hash_secret(code),
                             expires_at=now + timedelta(seconds=settings.mfa_ttl_seconds))
    db.add(challenge); db.flush()
    audit(db, "MFA_SENT", user.id, details="Código MFA emitido")
    # Em desenvolvimento o código é exibido na resposta para facilitar demonstração.
    return user, challenge, code if settings.app_env == "development" else None

def register_failure(db: Session, user: Investor, event: str):
    user.failed_attempts = (user.failed_attempts or 0) + 1
    if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
        user.blocked_until = datetime.now(timezone.utc) + timedelta(minutes=BLOCK_MINUTES)
        user.failed_attempts = 0
        audit(db, "ACCOUNT_BLOCKED", user.id, details=f"{MAX_FAILED_ATTEMPTS} falhas consecutivas")
    audit(db, event, user.id, details="Tentativa de autenticação inválida")

def verify_mfa(db: Session, challenge_id: int, code: str):
    challenge = db.get(MfaChallenge, challenge_id)
    if not challenge or challenge.used:
        raise BusinessError("Desafio MFA inválido ou já utilizado.")
    user = db.get(Investor, challenge.investor_id)
    if not user or not user.active:
        raise BusinessError("Desafio MFA inválido ou já utilizado.")
    now = datetime.now(timezone.utc)
    ensure_not_blocked(user, now)
    if as_utc(challenge.expires_at) < now or challenge.attempts >= MFA_MAX_ATTEMPTS:
        raise BusinessError("Código MFA expirado ou limite de tentativas atingido.")
    if not verify_secret(code, challenge.code_hash):
        challenge.attempts += 1
        register_failure(db, user, "MFA_FAILURE")
        raise BusinessError("Código MFA inválido.")
    challenge.used = True; user.failed_attempts = 0
    audit(db, "LOGIN_SUCCESS", user.id, details="Autenticação MFA concluída")
    return user

def portfolio(db: Session, investor_id: int):
    user = db.get(Investor, investor_id)
    rows = db.execute(
        select(Position, Asset.symbol).join(Asset, Asset.id == Position.asset_id)
        .where(Position.investor_id == investor_id, Position.quantity > 0)
        .order_by(Asset.symbol)).all()
    return {"balance": str(user.balance), "positions": [
        {"symbol": symbol, "quantity": p.quantity, "reserved_quantity": p.reserved_quantity,
         "available": p.quantity - p.reserved_quantity}
        for p, symbol in rows]}

def get_position(db: Session, investor_id: int, asset_id: int, create: bool = False):
    pos = db.scalar(select(Position).where(Position.investor_id == investor_id, Position.asset_id == asset_id))
    if pos is None and create:
        pos = Position(investor_id=investor_id, asset_id=asset_id, quantity=0, reserved_quantity=0)
        db.add(pos)
        db.flush()  # a sessão usa autoflush=False; sem isso uma 2ª consulta não enxergaria a posição nova
    return pos

def release_reservation(db: Session, investor: Investor, order: TradeOrder):
    """Devolve ao investidor a reserva (saldo ou posição) da ordem que ainda não foi consumida."""
    if order.side == Side.BUY.value:
        investor.balance = money(investor.balance) + money(order.reserved_cash)
        order.reserved_cash = Decimal("0")
    else:
        pos = get_position(db, investor.id, order.asset_id)
        if pos:
            pos.reserved_quantity = max(0, pos.reserved_quantity - order.reserved_quantity)
        order.reserved_quantity = 0

def place_order(db: Session, investor: Investor, data, now: datetime | None = None):
    existing = db.scalar(select(TradeOrder).where(
        TradeOrder.investor_id == investor.id, TradeOrder.idempotency_key == data.idempotency_key))
    if existing: return existing
    now = now or datetime.now(timezone.utc)
    ensure_not_blocked(investor, now)
    if not verify_secret(data.pin, investor.pin_hash):
        register_failure(db, investor, "PIN_FAILURE")
        raise BusinessError("PIN transacional inválido.")
    is_limit = data.order_type == OrderType.LIMIT
    if is_limit and data.limit_price is None:
        raise BusinessError("Ordens LIMIT exigem o campo limit_price.")
    asset = db.scalar(select(Asset).where(Asset.symbol == data.symbol.upper(), Asset.active.is_(True)))
    if not asset: raise BusinessError("Ativo inexistente ou indisponível.")
    quote = quotes.get_quote(asset)
    if (now - as_utc(quote.timestamp)).total_seconds() > settings.quote_max_age_seconds:
        raise BusinessError("Cotação desatualizada (limite de 10 segundos).")
    price = Decimal(str(data.limit_price)) if is_limit else quote.price
    value = money(price * data.quantity)
    if value > Decimal(str(investor.daily_order_limit)):
        raise BusinessError("Valor da ordem excede o limite por ordem.")
    if not is_trading_window(now, settings.trading_timezone):
        raise BusinessError("Ordens aceitas somente em dias úteis, das 10:00 às 17:55 (horário de Brasília).")
    local_now = now.astimezone(ZoneInfo(settings.trading_timezone))
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    exposure = db.scalar(select(func.coalesce(func.sum(TradeOrder.reference_price * TradeOrder.quantity), 0))
                         .where(TradeOrder.investor_id == investor.id, TradeOrder.created_at >= day_start,
                                TradeOrder.status.notin_(["REJECTED", "CANCELLED"]))) or 0
    if Decimal(str(exposure)) + value > Decimal(str(investor.daily_exposure_limit)):
        raise BusinessError("Exposição diária excede o limite configurado.")
    reserved_cash = Decimal("0"); reserved_qty = 0
    if data.side == Side.BUY:
        if money(investor.balance) < value: raise BusinessError("Saldo disponível insuficiente.")
        investor.balance = money(investor.balance) - value
        reserved_cash = value
    else:
        position = get_position(db, investor.id, asset.id)
        available = (position.quantity - position.reserved_quantity) if position else 0
        if available < data.quantity: raise BusinessError("Posição disponível insuficiente para venda.")
        position.reserved_quantity += data.quantity
        reserved_qty = data.quantity
    order = TradeOrder(investor_id=investor.id, asset_id=asset.id, side=data.side.value,
        order_type=data.order_type.value, quantity=data.quantity, limit_price=data.limit_price,
        reference_price=price, reserved_cash=reserved_cash, reserved_quantity=reserved_qty,
        status="CREATED", idempotency_key=data.idempotency_key)
    db.add(order); db.flush()
    db.add(OrderEvent(order_id=order.id, old_status=None, new_status="CREATED", message="Ordem criada"))
    change_status(db, order, OrderStatus.VALIDATED, "Validações concluídas")
    audit(db, "ORDER_CREATED", investor.id, order.id, f"{data.side.value} {data.quantity} {asset.symbol}")
    try:
        result = broker.submit(order.id, data.idempotency_key)
        if result != "ACCEPTED": raise BusinessError("Corretora simulada recusou a ordem.")
        change_status(db, order, OrderStatus.SENT, "Aceita pela corretora simulada")
    except Exception as exc:
        # Compensação de reserva em falha de transmissão.
        release_reservation(db, investor, order)
        change_status(db, order, OrderStatus.REJECTED, "Falha na transmissão")
        order.rejection_reason = "Falha na integração com a corretora."
        notify(db, investor, "Sua ordem foi rejeitada por indisponibilidade da integração.")
        raise BusinessError("Falha segura ao transmitir ordem; reserva liberada.") from exc
    notify(db, investor, f"Ordem {order.id} enviada para processamento simulado.")
    return order

def cancel_order(db: Session, investor: Investor, order: TradeOrder):
    if order.investor_id != investor.id: raise BusinessError("Ordem não encontrada.")
    status = OrderStatus(order.status)
    if status not in CANCELLABLE_STATES: raise BusinessError("Ordem não pode ser cancelada no estado atual.")
    if not broker.cancel(order.id, f"cancel-{order.id}"):
        raise BusinessError("Corretora não confirmou o cancelamento.")
    # RN-07: em ordem parcialmente executada só o saldo ainda não executado é liberado.
    release_reservation(db, investor, order)
    change_status(db, order, OrderStatus.CANCELLED, "Cancelamento confirmado pela corretora simulada")
    notify(db, investor, f"Ordem {order.id} cancelada.")
    return order

def apply_broker_update(db: Session, order: TradeOrder, status: OrderStatus, filled_quantity: int, message=""):
    if status not in {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.REJECTED}:
        raise BusinessError("Estado de retorno da corretora não permitido.")
    current = OrderStatus(order.status)
    # Webhooks repetidos da corretora são idempotentes (RN-08 / UC-12).
    if current == status and filled_quantity == order.filled_quantity:
        return order
    if current in FINAL_STATES:
        raise BusinessError("A ordem já está em estado final.")
    # Valida tudo antes de mexer em saldo ou carteira, para nunca deixar estado parcial.
    if status not in ALLOWED_TRANSITIONS[current]:
        raise BusinessError(f"Transição inválida: {current.value} -> {status.value}")
    if filled_quantity < order.filled_quantity or filled_quantity > order.quantity:
        raise BusinessError("Quantidade executada inválida.")
    if status == OrderStatus.FILLED and filled_quantity != order.quantity:
        raise BusinessError("Ordem executada exige quantidade executada igual à quantidade total.")
    if status == OrderStatus.PARTIALLY_FILLED and not 0 < filled_quantity < order.quantity:
        raise BusinessError("Execução parcial exige quantidade entre 1 e a quantidade total menos 1.")
    if status == OrderStatus.REJECTED and filled_quantity != 0:
        raise BusinessError("Ordem rejeitada não pode ter quantidade executada (RN-09).")
    investor = db.get(Investor, order.investor_id)
    delta = filled_quantity - order.filled_quantity
    if status == OrderStatus.REJECTED:
        release_reservation(db, investor, order)
        order.rejection_reason = message or "Rejeitada pela corretora"
    elif delta:
        price = Decimal(str(order.reference_price))
        if order.side == Side.BUY.value:
            pos = get_position(db, investor.id, order.asset_id, create=True)
            pos.quantity += delta
            order.reserved_cash = max(Decimal("0"), money(order.reserved_cash) - money(price * delta))
        else:
            pos = get_position(db, investor.id, order.asset_id)
            if pos is None or pos.quantity < delta:
                raise BusinessError("Posição insuficiente para registrar a execução da venda.")
            pos.quantity -= delta
            pos.reserved_quantity = max(0, pos.reserved_quantity - delta)
            order.reserved_quantity = max(0, order.reserved_quantity - delta)
            investor.balance = money(investor.balance) + money(price * delta)
    order.filled_quantity = filled_quantity
    change_status(db, order, status, message or "Atualização recebida da corretora")
    if status == OrderStatus.FILLED:
        # Sobras de arredondamento da reserva voltam ao investidor.
        release_reservation(db, investor, order)
    audit(db, "BROKER_UPDATE", investor.id, order.id, message)
    notify(db, investor, f"Ordem {order.id}: {status.value.lower()}.")
    return order
