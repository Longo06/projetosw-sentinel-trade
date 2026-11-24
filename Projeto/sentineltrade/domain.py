from datetime import datetime, time
from enum import Enum
from zoneinfo import ZoneInfo


class Role(str, Enum):
    INVESTOR = "INVESTOR"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"
    RISK_ANALYST = "RISK_ANALYST"


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SENT = "SENT"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


FINAL_STATES = {OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED}
CANCELLABLE_STATES = {
    OrderStatus.CREATED, OrderStatus.VALIDATED,
    OrderStatus.SENT, OrderStatus.PARTIALLY_FILLED
}
ALLOWED_TRANSITIONS = {
    OrderStatus.CREATED: {OrderStatus.VALIDATED, OrderStatus.REJECTED, OrderStatus.CANCELLED},
    OrderStatus.VALIDATED: {OrderStatus.SENT, OrderStatus.REJECTED, OrderStatus.CANCELLED},
    OrderStatus.SENT: {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED},
    # A corretora pode informar várias execuções parciais sucessivas (PARTIALLY_FILLED -> PARTIALLY_FILLED).
    OrderStatus.PARTIALLY_FILLED: {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELLED},
    OrderStatus.FILLED: set(), OrderStatus.REJECTED: set(), OrderStatus.CANCELLED: set(),
}

# RN-06: dias úteis, 10:00–17:55 (America/Sao_Paulo). Feriados não são considerados nesta versão.
TRADING_OPEN = time(10, 0)
TRADING_CLOSE = time(17, 55)


def is_trading_window(moment: datetime, tz_name: str = "America/Sao_Paulo") -> bool:
    """Indica se `moment` (datetime com fuso) está dentro da janela de negociação.

    A comparação é feita em minutos: 17:55:30 ainda pertence ao minuto 17:55 e é aceito.
    """
    local = moment.astimezone(ZoneInfo(tz_name))
    if local.weekday() >= 5:
        return False
    return TRADING_OPEN <= local.replace(second=0, microsecond=0).time() <= TRADING_CLOSE
