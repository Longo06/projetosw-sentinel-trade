from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import NoReturn
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from . import __version__
from .config import settings
from .db import Base, engine, get_db
from .models import Investor, Asset, TradeOrder, OrderEvent, AuditEvent, Notification
from .domain import Role
from .schemas import (InvestorCreate, InvestorUpdate, LoginRequest, MfaVerify, AssetCreate, AssetUpdate,
                      OrderCreate, RiskLimitUpdate, BrokerUpdate)
from .security import create_token, read_token
from .services import (BusinessError, audit, create_investor, login_start, verify_mfa, portfolio,
                       place_order, cancel_order, apply_broker_update)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SentinelTrade API", version=__version__, lifespan=lifespan,
              description="Plataforma acadêmica de negociação simulada. Não movimenta dinheiro real.")

bearer_scheme = HTTPBearer(auto_error=False)

@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/docs")

def fail(exc) -> NoReturn:
    if isinstance(exc, BusinessError): raise HTTPException(status_code=400, detail=str(exc))
    raise exc

def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    if not credentials:
        raise HTTPException(401, "Autenticação necessária.")

    identity = read_token(credentials.credentials)

    if not identity:
        raise HTTPException(401, "Sessão inválida ou expirada.")

    user = db.get(Investor, identity["id"])

    if not user or not user.active:
        raise HTTPException(401, "Usuário indisponível.")

    return user

def require_roles(*roles):
    allowed = [r.value if isinstance(r, Role) else r for r in roles]
    def dependency(user: Investor = Depends(current_user)):
        if user.role not in allowed:
            raise HTTPException(403, "Permissão insuficiente.")
        return user
    return dependency

def order_json(db, order):
    asset=db.get(Asset,order.asset_id)
    events=db.scalars(select(OrderEvent).where(OrderEvent.order_id==order.id).order_by(OrderEvent.id)).all()
    return {"id":order.id,"symbol":asset.symbol,"side":order.side,"type":order.order_type,
        "quantity":order.quantity,"filled_quantity":order.filled_quantity,"price":str(order.reference_price),
        "status":order.status,"rejection_reason":order.rejection_reason,"created_at":order.created_at,
        "events":[{"from":e.old_status,"to":e.new_status,"message":e.message,"at":e.created_at} for e in events]}

def user_orders(db: Session, user: Investor, limit: int, offset: int):
    stmt = (select(TradeOrder).where(TradeOrder.investor_id==user.id)
            .order_by(TradeOrder.created_at.desc(), TradeOrder.id.desc()).limit(limit).offset(offset))
    return [order_json(db,o) for o in db.scalars(stmt).all()]

@app.get("/health")
def health(): return {"status":"ok","mode":"simulated"}

@app.post("/api/investors", status_code=201)
def register(data: InvestorCreate, db: Session=Depends(get_db)):
    try:
        user=create_investor(db,data); db.commit()
        return {"id":user.id,"name":user.name,"email":user.email,"role":user.role}
    except BusinessError as e: db.rollback(); fail(e)

@app.get("/api/investors/me")
def me(user: Investor=Depends(current_user)):
    return {"id":user.id,"name":user.name,"email":user.email,"role":user.role,"active":user.active}

@app.patch("/api/investors/{investor_id}")
def update_investor(investor_id:int,data:InvestorUpdate, db:Session=Depends(get_db),
                    admin:Investor=Depends(require_roles(Role.ADMIN))):
    user=db.get(Investor,investor_id)
    if not user: raise HTTPException(404,"Investidor não encontrado.")
    for key,value in data.model_dump(exclude_unset=True).items(): setattr(user,key,value)
    audit(db,"INVESTOR_UPDATED",user.id,details=f"Alteração por administrador {admin.id}")
    db.commit()
    return {"id":user.id,"name":user.name,"active":user.active}

@app.post("/api/auth/login")
def login(data:LoginRequest,db:Session=Depends(get_db)):
    try:
        user,challenge,debug_code=login_start(db,data.email,data.password); db.commit()
        body={"message":"Código MFA emitido. Em produção, enviado por e-mail.","challenge_id":challenge.id}
        # O código só é exposto em desenvolvimento; em produção o campo é omitido.
        if debug_code is not None: body["debug_code"]=debug_code
        return body
    except BusinessError as e: db.commit(); fail(e)

@app.post("/api/auth/verify-mfa")
def verify(data:MfaVerify,db:Session=Depends(get_db)):
    try:
        user=verify_mfa(db,data.challenge_id,data.code); token=create_token(user.id,user.role); db.commit()
        return {"access_token":token,"token_type":"bearer","expires_in":settings.session_ttl_seconds}
    except BusinessError as e: db.commit(); fail(e)

@app.get("/api/portfolio")
def get_portfolio(db:Session=Depends(get_db),user:Investor=Depends(current_user)):
    return portfolio(db,user.id)

@app.get("/api/assets")
def list_assets(db:Session=Depends(get_db),user:Investor=Depends(current_user)):
    assets=db.scalars(select(Asset).where(Asset.active.is_(True)).order_by(Asset.symbol)).all()
    return [{"symbol":a.symbol,"name":a.name,"price":str(a.last_price),"quote_at":a.quote_at} for a in assets]

@app.post("/api/assets",status_code=201)
def add_asset(data:AssetCreate,db:Session=Depends(get_db),admin:Investor=Depends(require_roles(Role.ADMIN))):
    if db.scalar(select(Asset).where(Asset.symbol==data.symbol)):
        raise HTTPException(409,"Ativo já cadastrado.")
    asset=Asset(symbol=data.symbol,name=data.name,last_price=data.price,quote_at=datetime.now(timezone.utc))
    db.add(asset); db.flush(); audit(db,"ASSET_CREATED",admin.id,details=data.symbol); db.commit()
    return {"id":asset.id,"symbol":asset.symbol}

@app.patch("/api/assets/{asset_id}")
def edit_asset(asset_id:int,data:AssetUpdate,db:Session=Depends(get_db),admin:Investor=Depends(require_roles(Role.ADMIN))):
    asset=db.get(Asset,asset_id)
    if not asset: raise HTTPException(404,"Ativo não encontrado.")
    for k,v in data.model_dump(exclude_unset=True).items():
        if k=="price": asset.last_price=v; asset.quote_at=datetime.now(timezone.utc)
        else: setattr(asset,k,v)
    audit(db,"ASSET_UPDATED",admin.id,details=asset.symbol); db.commit()
    return {"id":asset.id,"symbol":asset.symbol,"active":asset.active,"price":str(asset.last_price)}

@app.post("/api/orders",status_code=201)
def create_order(data:OrderCreate,db:Session=Depends(get_db),user:Investor=Depends(current_user)):
    try:
        order=place_order(db,user,data); db.commit(); return order_json(db,order)
    except BusinessError as e: db.commit(); fail(e)

@app.get("/api/orders")
def list_orders(limit:int=Query(100,ge=1,le=500),offset:int=Query(0,ge=0),
                db:Session=Depends(get_db),user:Investor=Depends(current_user)):
    return user_orders(db,user,limit,offset)

@app.get("/api/orders/{order_id}")
def get_order(order_id:int,db:Session=Depends(get_db),user:Investor=Depends(current_user)):
    order=db.get(TradeOrder,order_id)
    if not order or (user.role==Role.INVESTOR.value and order.investor_id!=user.id):
        raise HTTPException(404,"Ordem não encontrada.")
    return order_json(db,order)

@app.post("/api/orders/{order_id}/cancel")
def cancel(order_id:int,db:Session=Depends(get_db),user:Investor=Depends(current_user)):
    order=db.get(TradeOrder,order_id)
    # Ordem de outro investidor é tratada como inexistente (404), sem revelar que ela existe.
    if not order or order.investor_id!=user.id: raise HTTPException(404,"Ordem não encontrada.")
    try:
        result=cancel_order(db,user,order); db.commit(); return order_json(db,result)
    except BusinessError as e: db.rollback(); fail(e)

@app.post("/api/orders/{order_id}/broker-update")
def broker_update(order_id:int,data:BrokerUpdate,db:Session=Depends(get_db),
                  admin:Investor=Depends(require_roles(Role.ADMIN,Role.RISK_ANALYST))):
    order=db.get(TradeOrder,order_id)
    if not order: raise HTTPException(404,"Ordem não encontrada.")
    try:
        result=apply_broker_update(db,order,data.status,data.filled_quantity,data.message)
        db.commit(); return order_json(db,result)
    except BusinessError as e: db.rollback(); fail(e)

@app.get("/api/audit")
def audit_list(investor_id:int|None=None,event_type:str|None=None,
               start:datetime|None=None,end:datetime|None=None,
               limit:int=Query(100,ge=1,le=500),
               db:Session=Depends(get_db),user:Investor=Depends(require_roles(Role.ADMIN,Role.AUDITOR))):
    stmt=select(AuditEvent)
    if investor_id is not None: stmt=stmt.where(AuditEvent.investor_id==investor_id)
    if event_type: stmt=stmt.where(AuditEvent.event_type==event_type)
    if start: stmt=stmt.where(AuditEvent.created_at>=start)
    if end: stmt=stmt.where(AuditEvent.created_at<=end)
    rows=db.scalars(stmt.order_by(AuditEvent.created_at.desc(),AuditEvent.id.desc()).limit(limit)).all()
    return [{"id":r.id,"investor_id":r.investor_id,"order_id":r.order_id,
             "event_type":r.event_type,"details":r.details,"created_at":r.created_at} for r in rows]

@app.patch("/api/admin/investors/{investor_id}/risk-limits")
def risk_limits(investor_id:int,data:RiskLimitUpdate,db:Session=Depends(get_db),
                admin:Investor=Depends(require_roles(Role.ADMIN))):
    user=db.get(Investor,investor_id)
    if not user: raise HTTPException(404,"Investidor não encontrado.")
    user.daily_order_limit=data.daily_order_limit; user.daily_exposure_limit=data.daily_exposure_limit
    audit(db,"RISK_LIMITS_UPDATED",user.id,details=f"Alterado pelo administrador {admin.id}")
    db.commit()
    return {"investor_id":user.id,"daily_order_limit":str(user.daily_order_limit),
            "daily_exposure_limit":str(user.daily_exposure_limit)}

@app.get("/api/notifications")
def notifications(limit:int=Query(100,ge=1,le=500),db:Session=Depends(get_db),user:Investor=Depends(current_user)):
    rows=db.scalars(select(Notification).where(Notification.investor_id==user.id)
                    .order_by(Notification.created_at.desc(),Notification.id.desc()).limit(limit)).all()
    return [{"id":n.id,"message":n.message,"status":n.status,"created_at":n.created_at} for n in rows]

@app.get("/api/history")
def history(limit:int=Query(100,ge=1,le=500),offset:int=Query(0,ge=0),
            db:Session=Depends(get_db),user:Investor=Depends(current_user)):
    return user_orders(db,user,limit,offset)
