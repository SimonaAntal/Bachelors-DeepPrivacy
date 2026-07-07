import os

from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import uuid

def generate_token(user_id, role):
    now = datetime.now(timezone.utc)

    payload = {
        "iss": os.getenv("JWT_ISSUER"),
        "sub": user_id,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=int(os.getenv("JWT_EXPIRATION_MINUTES")))
    }

    return jwt.encode(payload, os.getenv("JWT_SECRET_KEY"), algorithm=os.getenv("JWT_ALGORITHM"))

def extract_claims(token):
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=[os.getenv("JWT_ALGORITHM")])
        return payload
    except JWTError: # is_expired auto verified with jose
        return None

def valid_issuer(payload):
    return payload["iss"] == os.getenv("JWT_ISSUER")

def is_valid(token):
    payload = extract_claims(token)
    if payload is None:
        return False

    return valid_issuer(payload)

def extract_user_info(token):
    payload = extract_claims(token)

    if payload is None:
        return None

    return payload["sub"], payload["role"]