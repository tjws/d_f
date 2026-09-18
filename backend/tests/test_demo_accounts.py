import sys

import pytest
from sqlalchemy import select

from app.core.security import verify_password
from app.db.session import SessionLocal
from app.models.user import User
from scripts.ensure_demo_accounts import ensure_demo_accounts, main


def setup_function():
    with SessionLocal() as db:
        db.query(User).filter(User.username.in_(["demo_admin", "demo_manager", "demo_sales"])).delete(synchronize_session=False)
        db.commit()


def test_preview_does_not_create_demo_accounts():
    result = ensure_demo_accounts(apply=False, reset_passwords=False)

    assert result["missing"] == 3
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.username == "demo_sales")) is None


def test_apply_creates_accounts_and_explicit_reset_changes_password():
    created = ensure_demo_accounts(apply=True, reset_passwords=False)
    assert created["created"] == 3

    with SessionLocal() as db:
        sales = db.scalar(select(User).where(User.username == "demo_sales"))
        assert sales is not None
        old_hash = sales.hashed_password

    reset = ensure_demo_accounts(apply=True, reset_passwords=True)
    assert reset["reset"] == 3
    with SessionLocal() as db:
        sales = db.scalar(select(User).where(User.username == "demo_sales"))
        assert sales is not None
        assert sales.hashed_password != old_hash
        assert verify_password("Demo123456!", sales.hashed_password)


def test_reset_requires_apply():
    with pytest.raises(ValueError, match="--reset-passwords"):
        ensure_demo_accounts(apply=False, reset_passwords=True)


def test_cli_preview_does_not_print_password(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ensure_demo_accounts.py"])
    assert main() == 0
    assert "Demo123456!" not in capsys.readouterr().out
