"""Create (or reset the password of) an administrator account.

Admins cannot register through the website, so they are created on the server:
    python ../../deploy/create_admin.py admin@sirius.local "Администратор SIRIUS"
A strong random password is generated and printed once.
"""
import os
import secrets
import string
import sys
from datetime import datetime, timezone

# Run from backend/hackathon-hospital: make the app package importable.
sys.path.insert(0, os.getcwd())

from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.security import get_password_hash


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    email = sys.argv[1].strip().lower()
    full_name = sys.argv[2] if len(sys.argv) > 2 else "Администратор SIRIUS"
    alphabet = string.ascii_letters + string.digits
    password = "".join(secrets.choice(alphabet) for _ in range(20))

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user and user.role != "admin":
            print(f"{email} already exists with role '{user.role}'. Nothing changed.")
            return 1
        if not user:
            user = User(email=email, full_name=full_name, role="admin")
            db.add(user)
        user.password_hash = get_password_hash(password)
        user.terms_accepted_at = datetime.now(timezone.utc)
        user.terms_version = settings.LEGAL_DOCS_VERSION
        db.commit()
    finally:
        db.close()

    print(f"Admin account ready.\n  email:    {email}\n  password: {password}\nStore it safely; it is not saved anywhere else.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
