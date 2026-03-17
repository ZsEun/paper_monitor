from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException
import hashlib
import os
import boto3

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Cached JWT secret (lazy-loaded)
_cached_jwt_secret: Optional[str] = None


def get_jwt_secret() -> str:
    """Get JWT secret from Secrets Manager (cloud) or fallback to env/hardcoded (local)."""
    global _cached_jwt_secret
    if _cached_jwt_secret is not None:
        return _cached_jwt_secret

    secret_arn = os.environ.get("JWT_SECRET_ARN")
    if secret_arn:
        try:
            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId=secret_arn)
            _cached_jwt_secret = response["SecretString"]
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to retrieve JWT secret")
    else:
        _cached_jwt_secret = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")

    return _cached_jwt_secret

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using SHA256"""
    password_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return password_hash == hashed_password

def get_password_hash(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
