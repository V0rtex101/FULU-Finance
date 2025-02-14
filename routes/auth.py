from flask import Blueprint, request, render_template, redirect, session
from werkzeug.security import generate_password_hash

from services.db import register_user, get_user, update_user_password
from utils.helpers import apology

auth_bp = Blueprint("auth", __name__,
                    template_folder="templates",
                    url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return apology("Please provide username", 400)

        # Ensure password was submitted
        elif not password or not confirmation or password != confirmation:
            return apology("Both passwords must match", 400)

        # Query database for username
        try:
            hashed = generate_password_hash(password)
            register_user(username, hashed)
        except ValueError:
            return apology("Username already exists :(", 400)

        return redirect("/")
    else:
        return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Ensure username was submitted
        if not username:
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 403)

        # Query database for username
        try:
            user = get_user(username, password)
        except ValueError:
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = user["id"]

        # Redirect user to home page
        return redirect("/")
    else:
        return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@auth_bp.route("/change", methods=["GET", "POST"])
def change():
    if request.method == "POST":
        username = request.form.get("username")
        old_password = request.form.get("old")
        new_password = request.form.get("new")

        # Validate input
        if not username or not old_password or not new_password:
            return apology("Please provide username, old password, and new password", 400)

        if old_password == new_password:
            return apology("New password cannot be the same as the old password", 400)

        try:
            # Verify the old password
            get_user(username, old_password)

            # Update the password
            update_user_password(username, new_password)
            return redirect("/")
        except Exception as e:
            return apology(str(e), 400)

    else:
        return render_template("password.html")
