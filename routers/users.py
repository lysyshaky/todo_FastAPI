from datetime import datetime, timedelta
from typing import Annotated

from database import SessionLocal
from jose import JWTError, jwt
from models import Users
from passlib.context import CryptContext
from pydantic import BaseModel, Field
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


class UserVerification(BaseModel):
    password: str
    new_password: str = Field(min_length=6, max_length=20)


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


@router.put("/change_password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    user: user_dependency, db: db_dependency, user_verification: UserVerification
):
    if user is None:
        raise HTTPException(status_code=404, detail="Not Authenticated")
    user_model = db.query(Users).filter(Users.id == user.get("id")).first()
    if user_model is not None:
        if bcrypt_context.verify(
            user_verification.password, user_model.hashed_password
        ):
            user_model.hashed_password = bcrypt_context.hash(
                user_verification.new_password
            )
            db.add(user_model)
            db.commit()
            return
        raise HTTPException(status_code=401, detail="Wrong password")
    raise HTTPException(status_code=404, detail="User not found")


@router.post("/new_password", status_code=status.HTTP_200_OK)
async def new_password(user: user_dependency, db: db_dependency, password: str):
    if user is None:
        raise HTTPException(status_code=404, detail="Not Authenticated")
    user_model = db.query(Users).filter(Users.id == user.get("id")).first()
    if user_model is not None:
        user_model.hashed_password = bcrypt_context.hash(password)
        db.commit()
        return
    raise HTTPException(status_code=404, detail="User not found")
