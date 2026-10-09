"""Provision the first local FixFlow administrator account."""

from __future__ import annotations

from getpass import getpass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password, normalize_email
from app.db.session import get_session_factory
from app.models import User, UserRole


MIN_ADMIN_PASSWORD_LENGTH = 12


def main() -> None:
    """Interactively create one administrator without printing secrets."""

    full_name = input("Administrator full name: ").strip()
    if not full_name:
        raise SystemExit("A full name is required.")

    try:
        email = normalize_email(input("Administrator email: "))
    except ValueError as error:
        raise SystemExit(str(error)) from error

    password = getpass("Administrator password: ")
    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise SystemExit(
            f"Password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters."
        )
    if password != getpass("Confirm administrator password: "):
        raise SystemExit("Passwords do not match.")

    session = get_session_factory()()
    try:
        existing = session.scalar(
            select(User).where(func.lower(User.email) == email)
        )
        if existing is not None:
            raise SystemExit("An account with that email already exists.")

        session.add(
            User(
                full_name=full_name,
                email=email,
                password_hash=hash_password(password),
                role=UserRole.ADMINISTRATOR,
                is_active=True,
            )
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise SystemExit("That account could not be created because the email is already in use.") from error
    finally:
        session.close()

    print(f"Administrator account created for {email}.")


if __name__ == "__main__":
    main()
