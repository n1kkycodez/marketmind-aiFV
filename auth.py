"""
auth.py
Signup / login / logout / password reset, built on top of database.py.

Honesty notes on scope, so nothing here is mistaken for more than it is:

- Password hashing is real (bcrypt) — this part is production-grade.
- "Remember Me" here only keeps you logged in within the current browser
  tab's session (Streamlit's session_state). True persistence across
  browser restarts needs a signed cookie (e.g. the `extra-streamlit-
  components` package) — that's a small, well-scoped addition once you're
  ready for it, flagged again below at REMEMBER_ME_TODO.
- "Forgot Password" here is a simplified local flow (confirm username +
  email match, then set a new password) since there's no email-sending
  service wired up. A real implementation needs an email provider (e.g.
  SendGrid) and a publicly reachable app to receive the reset link.
"""

from __future__ import annotations
import re
import bcrypt
import streamlit as st

import database as db

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def sign_up(username: str, email: str, password: str) -> tuple[bool, str]:
    """Returns (success, message)."""
    username = username.strip()
    email = email.strip().lower()

    if not USERNAME_RE.match(username):
        return False, "Username must be 3-20 characters: letters, numbers, or underscores only."
    if not EMAIL_RE.match(email):
        return False, "Please enter a valid email address."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."

    if db.get_user_by_username(username):
        return False, "That username is already taken."
    if db.get_user_by_email(email):
        return False, "An account with that email already exists."

    user = db.create_user(username, email, _hash_password(password))
    if user is None:
        return False, "Something went wrong creating your account. Please try again."
    return True, "Account created! You can log in now."


def log_in(username_or_email: str, password: str) -> tuple[bool, str]:
    identifier = username_or_email.strip()
    user = db.get_user_by_username(identifier) or db.get_user_by_email(identifier.lower())

    if user is None or not _verify_password(password, user["password_hash"]):
        return False, "Incorrect username/email or password."

    # REMEMBER_ME_TODO: swap this for a signed cookie (extra-streamlit-components)
    # to survive browser restarts. For now this persists for the current
    # browser tab/session only.
    st.session_state["auth_user"] = {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "disclaimer_accepted": bool(user["disclaimer_accepted"]),
    }
    return True, f"Welcome back, {user['username']}!"


def log_out() -> None:
    st.session_state["auth_user"] = None


def current_user() -> dict | None:
    return st.session_state.get("auth_user")


def is_logged_in() -> bool:
    return current_user() is not None


def reset_password(username: str, email: str, new_password: str) -> tuple[bool, str]:
    """
    Simplified local password reset — confirms the username and email match
    an existing account, then sets a new password directly. This is NOT a
    substitute for a real email-verified reset flow; it's a reasonable
    stand-in for a local/personal app with no email service behind it.
    """
    user = db.get_user_by_username(username.strip())
    if user is None or user["email"].lower() != email.strip().lower():
        return False, "We couldn't find an account matching that username and email."
    if len(new_password) < 8:
        return False, "Password must be at least 8 characters."

    db.update_password(user["id"], _hash_password(new_password))
    return True, "Password updated. You can log in with your new password now."
