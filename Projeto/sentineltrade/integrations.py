"""Interfaces e adaptadores simulados. Substitua os adaptadores quando houver sandbox real."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass
from .models import Asset

@dataclass
class Quote:
    symbol: str
    price: Decimal
    timestamp: datetime

class QuoteProvider(ABC):
    @abstractmethod
    def get_quote(self, asset: Asset) -> Quote: ...

class SimulatedQuoteProvider(QuoteProvider):
    """Cotação simulada a partir do último preço persistido do ativo.

    Com `fresh=True` (padrão) o carimbo de tempo é o instante da consulta, simulando um feed
    ao vivo. Sem isso, a regra RN-11 (cotação com mais de 10 s é inválida) rejeitaria toda
    ordem enviada mais de 10 s depois do seed ou da última atualização de preço.
    Use `fresh=False` para simular uma cotação defasada (usa `asset.quote_at`).
    """

    def __init__(self, fresh: bool = True):
        self.fresh = fresh

    def get_quote(self, asset: Asset) -> Quote:
        if self.fresh:
            stamp = datetime.now(timezone.utc)
        elif asset.quote_at.tzinfo is None:
            stamp = asset.quote_at.replace(tzinfo=timezone.utc)
        else:
            stamp = asset.quote_at
        return Quote(asset.symbol, Decimal(str(asset.last_price)), stamp)

class Broker(ABC):
    @abstractmethod
    def submit(self, order_id: int, idempotency_key: str) -> str: ...
    @abstractmethod
    def cancel(self, order_id: int, idempotency_key: str) -> bool: ...

class SimulatedBroker(Broker):
    def submit(self, order_id: int, idempotency_key: str) -> str:
        # Aceite simulado; não representa execução financeira.
        return "ACCEPTED"
    def cancel(self, order_id: int, idempotency_key: str) -> bool:
        return True

class NotificationGateway(ABC):
    @abstractmethod
    def send(self, destination: str, message: str) -> None: ...

class ConsoleNotificationGateway(NotificationGateway):
    def send(self, destination: str, message: str) -> None:
        print(f"[NOTIFICAÇÃO SIMULADA para {destination}] {message}")
