from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import User
from app.services.auth import get_user_by_email, create_user, authenticate_user, verify_password, hash_password

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
@limiter.limit("5/minute")
def signup_submit(
    request: Request,
    name: str = Form(..., max_length=100),
    email: str = Form(..., max_length=254),
    password: str = Form(..., max_length=128),
    db: Session = Depends(get_db)
):
    existing_user = get_user_by_email(db, email)

    if existing_user:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {"request": request, "error": "An account with that email already exists."}
        )

    if len(password) < 10:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {"request": request, "error": "Password must be at least 10 characters."}
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
@limiter.limit("10/minute")
def login_submit(
    request: Request,
    email: str = Form(..., max_length=254),
    password: str = Form(..., max_length=128),
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


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    user = db.query(User).filter(User.id == user_id).first()
    return templates.TemplateResponse(request, "profile.html", {
        "request": request,
        "current_user": user,
        "success": None,
        "error": None,
    })


@router.post("/profile", response_class=HTMLResponse)
def profile_update(
    request: Request,
    name: str = Form(...),
    current_password: str = Form(default=""),
    new_password: str = Form(default=""),
    confirm_password: str = Form(default=""),
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    user = db.query(User).filter(User.id == user_id).first()

    def render(error=None, success=None):
        return templates.TemplateResponse(request, "profile.html", {
            "request": request,
            "current_user": user,
            "error": error,
            "success": success,
        })

    name = name.strip()
    if not name:
        return render(error="Name cannot be empty.")

    if new_password:
        if not current_password:
            return render(error="Enter your current password to set a new one.")
        if not verify_password(current_password, user.password_hash):
            return render(error="Current password is incorrect.")
        if new_password != confirm_password:
            return render(error="New passwords do not match.")
        if len(new_password) < 10:
            return render(error="New password must be at least 10 characters.")
        user.password_hash = hash_password(new_password)

    user.name = name
    db.commit()
    request.session["user_name"] = user.name

    return render(success="Profile updated successfully.")