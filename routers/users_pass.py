import sys
from re import template

sys.path.append("..")

import models
from database import SessionLocal, engine
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import Response

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .auth import get_current_user, get_password_hash, verify_password

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not Found"}},
)

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


class UserVerification(BaseModel):
    username: str
    password: str
    new_password: str


@router.get("/edit-password", response_class=HTMLResponse)
async def edit_user_view(request: Request):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    # Check if user is a dict or an SQLAlchemy model instance
    user_data = user if isinstance(user, dict) else user.__dict__

    return templates.TemplateResponse(
        "edit-user-password.html", {"request": request, "user": user_data}
    )


@router.post("/edit-user-password", response_class=HTMLResponse)
async def user_password_change(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    user_data = db.query(models.Users).filter(models.Users.username == username).first()

    msg = "Invalid username or password"

    if user_data is not None:
        if username == user_data.username and verify_password(
            password, user_data.hashed_password
        ):
            user_data.hashed_password = get_password_hash(new_password)
            db.add(user_data)
            db.commit()
            msg = "Password updated"

    return templates.TemplateResponse(
        "edit-user-password.html", {"request": request, "user": user, "msg": msg}
    )
