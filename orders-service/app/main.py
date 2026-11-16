import logging
import os
import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from .models import User
from .auth import get_current_user, hash_password, verify_password, create_access_token, unauthorized
from sqlalchemy.orm import Session
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from . import crud, schemas, models
from .database import Base, engine, get_db

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orders-api")
FORECAST_URL = os.getenv("FORECAST_URL", "http://forecast-api:8001")
FORECAST_TIMEOUT = float(os.getenv("FORECAST_TIMEOUT", "3.0"))
PROPERTY_FIELDS = {"gr_liv_area", "total_bsmt_sf", "garage_area", "year_built", "overall_qual", "ms_zoning"}
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Orders API", version="0.2.0")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.3, max=2), retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)), reraise=True)
def _request_prediction(payload: dict) -> float:
    response = httpx.post(f"{FORECAST_URL}/predict", json=payload, timeout=FORECAST_TIMEOUT)
    response.raise_for_status()
    return float(response.json()["predicted_price"])

def predict_or_none(payload: dict) -> float | None:
    try:
        return _request_prediction(payload)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        logger.warning("Prediction unavailable; saving without a price: %s", exc)
        return None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post('/auth/register', response_model=schemas.UserOut, status_code=201)
def register(data: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == data.username)) is not None:
        raise HTTPException(status_code=409, detail='Username already registered')
    user = User(username=data.username, hashed_password=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        from sqlalchemy.exc import IntegrityError
        if isinstance(exc, IntegrityError):
            raise HTTPException(status_code=409, detail='Username already registered') from exc
        raise
    db.refresh(user)
    return user


@app.post('/auth/login', response_model=schemas.TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == form.username))
    if user is None or not verify_password(form.password, user.hashed_password) or not user.is_active:
        raise HTTPException(status_code=401, detail='Incorrect username or password', headers={'WWW-Authenticate': 'Bearer'})
    return schemas.TokenOut(access_token=create_access_token(user.username))


@app.get('/auth/me', response_model=schemas.UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/orders", response_model=schemas.OrderRead, status_code=201)
def create_order(data: schemas.OrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    price = predict_or_none({k: getattr(data, k) for k in PROPERTY_FIELDS})
    return crud.create_order(db, data, price)

@app.get("/orders", response_model=list[schemas.OrderRead])
def list_orders(limit: int = 20, offset: int = 0, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100.")
    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be non-negative.")
    return crud.list_orders(db, limit, offset)

@app.get("/orders/{oid}", response_model=schemas.OrderRead)
def get_order(oid: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = crud.get_order(db, oid)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order

@app.patch("/orders/{oid}", response_model=schemas.OrderRead)
def update_order(oid: int, data: schemas.OrderUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = crud.get_order(db, oid)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    changes = data.model_dump(exclude_unset=True)
    property_changed = any(k in PROPERTY_FIELDS and getattr(order, k) != v for k, v in changes.items())
    if property_changed:
        merged = {k: changes.get(k, getattr(order, k)) for k in PROPERTY_FIELDS}
        # Invalidate the previous prediction when inputs change, even if forecast is down.
        changes["predicted_price"] = predict_or_none(merged)
    return crud.update_order(db, order, changes)

@app.delete("/orders/{oid}", status_code=204)
def delete_order(oid: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = crud.get_order(db, oid)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    crud.delete_order(db, order)
