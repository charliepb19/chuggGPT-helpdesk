from app.database import SessionLocal, engine
from app import models
from app.services.auth import get_user_by_email, create_user


def main():
    # Make sure all tables exist before querying users
    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    email = "admin@example.com"
    existing = get_user_by_email(db, email)

    if existing:
        existing.role = "admin"
        db.commit()
        print(f"Updated existing user {email} to admin.")
    else:
        create_user(
            db=db,
            name="Admin",
            email=email,
            password="admin123",
            role="admin"
        )
        print("Created admin account:")
        print("Email: admin@example.com")
        print("Password: admin123")

    db.close()


if __name__ == "__main__":
    main()