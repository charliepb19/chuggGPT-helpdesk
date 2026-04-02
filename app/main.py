from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.routes import tickets, dashboard, auth, chat
from app.database import engine
from app import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chugg AI Helpdesk")

app.add_middleware(SessionMiddleware, secret_key="super-secret-key-change-this-later")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(dashboard.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return RedirectResponse(url="/login")