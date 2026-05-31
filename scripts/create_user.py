#!/usr/bin/env python3
"""Create initial admin user."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.auth import hash_password
from backend.db.models import User
from backend.db.session import SessionLocal, init_db


def main():
    init_db()
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@autovideo.local"
    password = sys.argv[2] if len(sys.argv) > 2 else "admin123"
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print(f"User {email} already exists")
            return
        db.add(User(email=email, password_hash=hash_password(password)))
        db.commit()
        print(f"Created user: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
