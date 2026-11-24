"""Cria dados fictícios para demonstração local (somente com APP_ENV=development)."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from sentineltrade.config import settings
from sentineltrade.db import Base, SessionLocal, engine
from sentineltrade.models import Asset, Investor
from sentineltrade.security import hash_secret

DEMO_USERS = [
    # nome, e-mail, senha, perfil, saldo inicial
    ("Administrador Demo", "admin@sentineltrade.local", "Admin123!", "ADMIN", "0"),
    ("Investidor Demo", "investidor@sentineltrade.local", "Invest123!", "INVESTOR", "100000"),
    ("Auditor Demo", "auditor@sentineltrade.local", "Audit123!", "AUDITOR", "0"),
    ("Analista de Risco Demo", "risco@sentineltrade.local", "Risk123!", "RISK_ANALYST", "0"),
]
DEMO_PIN = "1234"
DEMO_ASSETS = [("PETR4", "Petrobras PN", "38.50"), ("VALE3", "Vale ON", "62.30"),
               ("ITUB4", "Itaú Unibanco PN", "34.20"), ("BOVA11", "ETF Ibovespa", "125.00")]


def main() -> None:
    if settings.app_env != "development":
        raise SystemExit("seed.py cria contas com senhas conhecidas e só pode rodar com APP_ENV=development.")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for name, email, password, role, balance in DEMO_USERS:
            if not db.scalar(select(Investor).where(Investor.email == email)):
                db.add(Investor(name=name, email=email, password_hash=hash_secret(password),
                                pin_hash=hash_secret(DEMO_PIN), role=role, balance=Decimal(balance)))
        for symbol, name, price in DEMO_ASSETS:
            if not db.scalar(select(Asset).where(Asset.symbol == symbol)):
                db.add(Asset(symbol=symbol, name=name, last_price=Decimal(price),
                             quote_at=datetime.now(timezone.utc)))
        db.commit()
    finally:
        db.close()

    print("Dados de demonstração criados.")
    for name, email, password, role, _ in DEMO_USERS:
        print(f"{role}: {email} / {password}")
    print(f"PIN transacional de todos: {DEMO_PIN}")


if __name__ == "__main__":
    main()
