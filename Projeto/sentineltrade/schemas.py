from decimal import Decimal
from pydantic import BaseModel, Field, model_validator
from .domain import Side, OrderType, OrderStatus

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

class InvestorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=180)
    password: str = Field(min_length=8, max_length=128)
    pin: str = Field(pattern=r"^\d{4,8}$")

class InvestorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    active: bool | None = None

class LoginRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=180)
    # Limite de tamanho evita custo excessivo de PBKDF2 com entradas gigantes.
    password: str = Field(min_length=1, max_length=128)

class MfaVerify(BaseModel):
    challenge_id: int
    code: str = Field(pattern=r"^\d{6}$")

class AssetCreate(BaseModel):
    symbol: str = Field(min_length=3, max_length=20, pattern=r"^[A-Z0-9]+$")
    name: str = Field(min_length=2, max_length=120)
    price: Decimal = Field(gt=0)

class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    price: Decimal | None = Field(default=None, gt=0)
    active: bool | None = None

class OrderCreate(BaseModel):
    symbol: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9]+$")
    side: Side
    quantity: int = Field(gt=0, le=1_000_000)
    order_type: OrderType = OrderType.MARKET
    limit_price: Decimal | None = Field(default=None, gt=0)
    idempotency_key: str = Field(min_length=8, max_length=100)
    pin: str = Field(pattern=r"^\d{4,8}$")

class RiskLimitUpdate(BaseModel):
    daily_order_limit: Decimal = Field(gt=0, le=1_000_000)
    daily_exposure_limit: Decimal = Field(gt=0, le=10_000_000)

    @model_validator(mode="after")
    def exposure_not_below_order_limit(self):
        if self.daily_exposure_limit < self.daily_order_limit:
            raise ValueError("O limite de exposição diária não pode ser menor que o limite por ordem.")
        return self

class BrokerUpdate(BaseModel):
    # Tipado como enum: valor inválido vira 422 em vez de erro de conversão manual.
    status: OrderStatus
    filled_quantity: int = Field(default=0, ge=0)
    message: str = Field(default="", max_length=500)
