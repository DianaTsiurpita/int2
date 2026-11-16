import os
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import get_db, read_secret
from .models import User

JWT_SECRET = read_secret('jwt_secret_key')  # mandatory: no environment fallback
ALGORITHM = 'HS256'
TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
if TOKEN_EXPIRE_MINUTES <= 0:
    raise RuntimeError('ACCESS_TOKEN_EXPIRE_MINUTES must be positive')
password_hash = PasswordHash.recommended()  # Argon2id
bearer = OAuth2PasswordBearer(tokenUrl='auth/login')


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': username, 'iat': now, 'exp': now + timedelta(minutes=TOKEN_EXPIRE_MINUTES)}, JWT_SECRET, algorithm=ALGORITHM)


def unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate credentials', headers={'WWW-Authenticate': 'Bearer'})


def get_current_user(token: str = Depends(bearer), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        username = payload.get('sub')
        if not isinstance(username, str) or not username:
            raise unauthorized()
    except jwt.PyJWTError:
        raise unauthorized()
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active:
        raise unauthorized()
    return user
