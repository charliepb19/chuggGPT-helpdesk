from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_user_by_email, create_user, authenticate_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse(
        request,
        "signup.html",
        {"request": request, "error": None}
    )


@router.post("/signup", response_class=HTMLResponse)
def signup_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing_user = get_user_by_email(db, email)

    if existing_user:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {
                "request": request,
                "error": "An account with that email already exists."
            }
        )

    create_user(db, name=name, email=email, password=password, role="user")

    return RedirectResponse(url="/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "error": None}
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, email, password)

    if not user:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "error": "Invalid email or password."
            }
        )

    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["user_role"] = user.role

    if user.role == "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

    return RedirectResponse(url="/submit-ticket", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)