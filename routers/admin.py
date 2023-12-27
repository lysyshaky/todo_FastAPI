from typing import Annotated

from database import SessionLocal
from models import Todos
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette import status

from fastapi import APIRouter, Depends, HTTPException, Path

from .auth import get_current_user

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
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


@router.get("/todo", status_code=status.HTTP_200_OK)
async def read_all(user: user_dependency, db: db_dependency):
    if user is None or user.get("user_role") != "admin":
        raise HTTPException(
            status_code=401,
            detail="You don't have admin permissions or not authenticated",
        )
    return db.query(Todos).all()


@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)
):
    if user is None or user.get("user_role") != "admin":
        raise HTTPException(
            status_code=401,
            detail="You don't have admin permissions or not authenticated",
        )
    todo_model = db.query(Todos).filter(Todos.id == todo_id).first()
    if todo_model is not None:
        db.delete(todo_model)
        db.commit()
        return
    raise HTTPException(status_code=404, detail="Todo not found")
