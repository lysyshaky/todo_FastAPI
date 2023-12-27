from datetime import datetime, timedelta
from typing import Annotated, Optional

import models
from database import SessionLocal
from jose import JWTError, jwt
from models import Users
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


class LoginForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.username: Optional[str] = None
        self.password: Optional[str] = None

    async def create_oauth_form(self):
        form = await self.request.form()
        self.username = form.get("email")
        self.password = form.get("password")


SECRET_KEY = "3a027009798e29ada24ab5c7e4bd74c73928f08aaa205127ddca07226053057a"
ALGORITHM = "HS256"

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")


templates = Jinja2Templates(directory="templates")


class CreateUserRequest(BaseModel):
    email: str
    role: str
    username: str
    first_name: str
    last_name: str
    password: str
    phone_number: str


class Token(BaseModel):
    access_token: str
    token_type: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# dependency injection

db_dependency = Annotated[Session, Depends(get_db)]


def get_password_hash(password):
    return bcrypt_context.hash(password)


def verify_password(plain_password, hashed_password):
    return bcrypt_context.verify(plain_password, hashed_password)


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user


def create_access_token(
    role: str, username: str, user_id: int, expires_delta: timedelta
):
    encode = {"sub": username, "id": user_id, "role": role}
    expire = datetime.utcnow() + expires_delta
    encode.update({"exp": expire})
    encoded_jwt = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(request: Request) -> Optional[dict]:
    try:
        token = request.cookies.get("access_token")
        if token is None:
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if "sub" not in payload or "id" not in payload:
            return logout(request)
        return {"username": payload["sub"], "id": payload["id"]}
    except JWTError:
        return HTTPException(status_code=404, detail="Not found")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    create_user_model = Users(
        email=create_user_request.email,
        username=create_user_request.username,
        role=create_user_request.role,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        hashed_password=bcrypt_context.hash(create_user_request.password),
        is_active=True,
        phone_number=create_user_request.phone_number,
    )
    db.add(create_user_model)
    db.commit()


@router.post("/token", response_model=Token)
async def login_for_asses_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency,
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # raise HTTPException(
        #     status_code=status.HTTP_401_UNAUTHORIZED,
        #     detail="Incorrect username or password",
        # )
        raise False
    token = create_access_token(
        user.role,
        user.username,
        user.id,
        timedelta(minutes=60),
    )

    response.set_cookie(key="access_token", value=token, httponly=True)
    return True
    # return {"access_token": token, "token_type": "bearer"}


@router.get("/", response_class=HTMLResponse)
async def auth_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = form.get("email")
    password = form.get("password")

    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html", {"request": request, "msg": "Incorrect username or password"}
        )

    token = create_access_token(
        user.role, user.username, user.id, timedelta(minutes=60)
    )

    response = RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response


@router.get("/logout")
async def logout(request: Request):
    msg = "Logout Successful"
    response = templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "msg": msg,
        },
    )
    response.delete_cookie(key="access_token")
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register", response_class=HTMLResponse)
async def register_user(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    firstname: str = Form(...),
    lastname: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    db: Session = Depends(get_db),
):
    validation1 = (
        db.query(models.Users).filter(models.Users.username == username).first()
    )

    validation2 = db.query(models.Users).filter(models.Users.email == email).first()

    if password != password2 is not None or validation2 is not None:
        msg = "Invalid registration request"
        return templates.TemplateResponse(
            "register.html", {"request": request, "msg": msg}
        )
    user_model = models.Users()
    user_model.username = username
    user_model.email = email
    user_model.firstname = firstname
    user_model.lastname = lastname

    hash_password = get_password_hash(password)
    user_model.hashed_password = hash_password
    user_model.is_active = True

    db.add(user_model)
    db.commit()
    msg = "User successfully created"
    return templates.TemplateResponse("login.html", {"request": request, "msg": msg})
