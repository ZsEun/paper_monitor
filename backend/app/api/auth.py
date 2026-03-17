from fastapi import APIRouter, HTTPException, status
from app.models.schemas import UserCreate, UserLogin, User, Token
from app.utils.storage import read_json_file, write_json_file
from app.utils.security import get_password_hash, verify_password, create_access_token
from datetime import timedelta
import uuid

router = APIRouter()

USERS_FILE = "users.json"

@router.post("/register", response_model=Token)
def register(user: UserCreate):
    users = read_json_file(USERS_FILE)
    
    # Check if user already exists
    if user.email in users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user.password)
    
    users[user.email] = {
        "id": user_id,
        "email": user.email,
        "name": user.name,
        "password": hashed_password
    }
    
    write_json_file(USERS_FILE, users)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user.email,
            "name": user.name
        }
    }

@router.post("/login", response_model=Token)
def login(credentials: UserLogin):
    users = read_json_file(USERS_FILE)
    
    # Check if user exists
    if credentials.email not in users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    user_data = users[credentials.email]
    
    # Verify password
    if not verify_password(credentials.password, user_data["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": credentials.email},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_data["id"],
            "email": user_data["email"],
            "name": user_data["name"]
        }
    }

@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}
