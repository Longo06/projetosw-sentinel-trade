"""Configuração compartilhada dos testes.

As variáveis de ambiente precisam ser definidas ANTES de importar `sentineltrade`, porque o
engine do banco é criado na importação. Os testes usam um SQLite temporário, nunca o banco local.
"""
import os
import tempfile
from pathlib import Path

_TMP_DIR = tempfile.mkdtemp(prefix="sentineltrade-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{(Path(_TMP_DIR) / 'test.db').as_posix()}"
os.environ["APP_ENV"] = "development"
os.environ["SECRET_KEY"] = "chave-somente-para-testes-com-mais-de-32-caracteres"

from decimal import Decimal  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402

from sentineltrade import models  # noqa: E402,F401  (registra as tabelas no metadata)
from sentineltrade.db import Base, SessionLocal, engine  # noqa: E402
from sentineltrade.domain import OrderType, Side  # noqa: E402
from sentineltrade.models import Asset, Investor  # noqa: E402
from sentineltrade.security import hash_secret  # noqa: E402

PASSWORD = "Senha-Forte-1"
PIN = "1234"


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def make_user(db, email="investidor@teste.local", role="INVESTOR", balance="100000"):
    user = Investor(name="Usuário Teste", email=email, password_hash=hash_secret(PASSWORD),
                    pin_hash=hash_secret(PIN), role=role, balance=Decimal(balance))
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def investor(db):
    return make_user(db)


@pytest.fixture
def asset(db):
    item = Asset(symbol="PETR4", name="Petrobras PN", last_price=Decimal("38.50"))
    db.add(item)
    db.commit()
    return item


@pytest.fixture
def market_open(monkeypatch):
    """Força a janela de negociação aberta (a regra de horário tem testes próprios)."""
    monkeypatch.setattr("sentineltrade.services.is_trading_window", lambda *args, **kwargs: True)


_counter = {"n": 0}


def order_data(**overrides):
    """Dados de ordem no formato aceito por `place_order` (chave de idempotência sempre nova)."""
    _counter["n"] += 1
    data = dict(symbol="PETR4", side=Side.BUY, quantity=10, order_type=OrderType.MARKET,
                limit_price=None, idempotency_key=f"chave-teste-{_counter['n']:06d}", pin=PIN)
    data.update(overrides)
    return SimpleNamespace(**data)
