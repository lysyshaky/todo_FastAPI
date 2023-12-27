from typing import Annotated

import models
from database import SessionLocal, engine
from models import Todos
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette import status

from fastapi import APIRouter, Depends, Form, HTTPException, Path, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .auth import get_current_user

router = APIRouter(
    prefix="/todos",
    tags=["todos"],
    responses={404: {"description": "Not found"}},
)

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_class=HTMLResponse)
async def read_all_by_user(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    todos = db.query(models.Todos).filter(models.Todos.owner_id == user["id"]).all()
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "todos": todos, "user": user},
    )


@router.get("/add-todo", response_class=HTMLResponse)
async def add_new_todo(request: Request):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        "add-todo.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.post("/add-todo", response_class=HTMLResponse)
async def create_todo(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    priority: int = Form(...),
    db: Session = Depends(get_db),
):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)
    todo_model = models.Todos()
    todo_model.title = title
    todo_model.description = description
    todo_model.priority = priority
    todo_model.complete = False
    todo_model.owner_id = user.get("id")

    db.add(todo_model)
    db.commit()

    return RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)


@router.get("/edit-todo/{todo_id}", response_class=HTMLResponse)
async def edit_todo(request: Request, todo_id: int, db: Session = Depends(get_db)):
    todo = db.query(models.Todos).filter(models.Todos.id == todo_id).first()
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        "edit-todo.html",
        {
            "request": request,
            "todo": todo,
            "user": user,
        },
    )


@router.post("/edit-todo/{todo_id}", response_class=HTMLResponse)
async def edit_todo_commit(
    request: Request,
    todo_id: int,
    title: str = Form(...),
    description: str = Form(...),
    priority: int = Form(...),
    db: Session = Depends(get_db),
):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)
    todo = db.query(models.Todos).filter(models.Todos.id == todo_id).first()
    todo.title = title
    todo.description = description
    todo.priority = priority

    db.add(todo)
    db.commit()

    return RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)


@router.get("/delete-todo/{todo_id}", response_class=HTMLResponse)
async def delete_todo(request: Request, todo_id: int, db: Session = Depends(get_db)):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)
    todo = (
        db.query(models.Todos)
        .filter(models.Todos.id == todo_id)
        .filter(models.Todos.owner_id == user["id"])
        .first()
    )
    db.delete(todo)
    db.commit()

    return RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)


@router.get("/complete/{todo_id}", response_class=HTMLResponse)
async def complete_todo(request: Request, todo_id: int, db: Session = Depends(get_db)):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)
    todo = db.query(models.Todos).filter(models.Todos.id == todo_id).first()
    if todo:
        todo.complete = not todo.complete
        db.add()
        db.commit()
    return RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)


# # dependency injection
# db_dependency = Annotated[Session, Depends(get_db)]

# user_dependency = Annotated[Session, Depends(get_current_user)]


# class TodoRequest(BaseModel):
#     title: str = Field(min_length=3)
#     description: str = Field(min_length=3, max_length=100)
#     priority: int = Field(gt=0, lt=6)
#     complete: bool


# @router.get("/test")
# async def test(request: Request):
#     return templates.TemplateResponse("register.html", {"request": request})


# @router.get("/", status_code=status.HTTP_200_OK)
# async def read_all(user: user_dependency, db: db_dependency):
#     if user is None:
#         raise HTTPException(status_code=404, detail="Not Authenticated")
#     return db.query(Todos).filter(Todos.owner_id == user.get("id")).all()


# @router.get("/todo/{todo_id}")
# async def read_todo(
#     user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)
# ):
#     if user is None:
#         raise HTTPException(status_code=404, detail="Not Authenticated")
#     todo_model = (
#         db.query(Todos)
#         .filter(Todos.id == todo_id)
#         .filter(Todos.owner_id == user.get("id"))
#         .first()
#     )
#     if todo_model is not None:
#         return todo_model
#     raise HTTPException(status_code=404, detail="Todo not found")


# @router.post("/todo", status_code=status.HTTP_201_CREATED)
# async def create_todo(
#     user: user_dependency, db: db_dependency, todo_request: TodoRequest
# ):
#     if user is None:
#         raise HTTPException(status_code=404, detail="Not Authenticated")
#     todo_model = Todos(**todo_request.model_dump(), owner_id=user.get("id"))
#     db.add(todo_model)
#     db.commit()
#     db.refresh(todo_model)
#     return todo_model


# @router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def update_todo(
#     user: user_dependency,
#     db: db_dependency,
#     todo_request: TodoRequest,
#     todo_id: int = Path(gt=0),
# ):
#     if user is None:
#         raise HTTPException(status_code=404, detail="Not Authenticated")
#     todo_model = (
#         db.query(Todos)
#         .filter(Todos.id == todo_id)
#         .filter(Todos.owner_id == user.get("id"))
#         .first()
#     )
#     if todo_model is not None:
#         todo_model.title = todo_request.title
#         todo_model.description = todo_request.description
#         todo_model.priority = todo_request.priority
#         todo_model.complete = todo_request.complete
#         db.add(todo_model)
#         db.commit()
#         return
#     raise HTTPException(status_code=404, detail="Todo not found")


# @router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_todo(
#     user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)
# ):
#     if user is None:
#         raise HTTPException(status_code=404, detail="Not Authenticated")

#     todo_model = (
#         db.query(Todos)
#         .filter(Todos.id == todo_id)
#         .filter(Todos.owner_id == user.get("id"))
#         .first()
#     )
#     if todo_model is not None:
#         db.delete(todo_model)
#         db.commit()
#         return
#     raise HTTPException(status_code=404, detail="Todo not found")
