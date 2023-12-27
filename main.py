# main.py
import models
from database import engine
from routers import admin, auth, todos, users, users_pass
from starlette import status
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from fastapi import Depends, FastAPI

app = FastAPI()


@app.on_event("startup")
def startup_event():
    models.Base.metadata.create_all(bind=engine)


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/todos", status_code=status.HTTP_302_FOUND)


app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(users_pass.router)
