import getpass
from app.database import SessionLocal, engine
from app import models
from app.services.auth import get_user_by_email, create_user, hash_password


def main():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("=== Create Admin Account ===")
    email = input("Email: ").strip()
    name = input("Name: ").strip()
    password = getpass.getpass("Password: ")

    if not email or not name or not password:
        print("All fields are required.")
        db.close()
        return

    existing = get_user_by_email(db, email)
    if existing:
        existing.role = "admin"
        existing.name = name
        existing.password_hash = hash_password(password)
        db.commit()
        print(f"Updated {email} to admin.")
    else:
        create_user(db=db, name=name, email=email, password=password, role="admin")
        print(f"Admin account created for {email}.")

    db.close()


if __name__ == "__main__":
    main()
