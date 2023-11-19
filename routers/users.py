from datetime import datetime, timedelta
from typing import Annotated

from database import SessionLocal
from jose import JWTError, jwt
from models import Users
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from .auth import get_current_user

router = APIRouter(
    prefix="/user",
    tags=["user"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# dependency injection
db_dependency = Annotated[Session, Depends(get_db)]

user_dependency = Annotated[Session, Depends(get_current_user)]


bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/", status_code=status.HTTP_200_OK)
async def get_user(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=404, detail="Not Authenticated")
    user_model = db.query(Users).filter(Users.id == user.get("id")).first()
    if user_model is not None:
        return user_model
    raise HTTPException(status_code=404, detail="User not found")


@router.get("/all_users", status_code=status.HTTP_200_OK)
async def get_all_users(user: user_dependency, db: db_dependency):
    if user is None or user.get("user_role") != "admin":
        raise HTTPException(status_code=404, detail="You don't have admin permissions")
    return db.query(Users).all()


@router.post("change_password", status_code=status.HTTP_200_OK)
async def change_password(user: user_dependency, db: db_dependency, password: str):
    if user is None:
        raise HTTPException(status_code=404, detail="Not Authenticated")
    user_model = db.query(Users).filter(Users.id == user.get("id")).first()
    if user_model is not None:
        user_model.hashed_password = bcrypt_context.hash(password)
        db.commit()
        return
    raise HTTPException(status_code=404, detail="User not found")
