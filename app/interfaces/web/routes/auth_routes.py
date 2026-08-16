from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.domain.entities.user import UserRole
from app.domain.errors import AuthenticationError, AuthorizationError, ValidationError
from app.extensions import limiter
from app.interfaces.web.routes.utils import current_actor, get_services, get_use_cases

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
DASHBOARD_HOME = "dashboard.home"


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per 15 minutes", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(DASHBOARD_HOME))

    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")

        try:
            user = get_use_cases().login_user.execute(email, password)
            login_user(get_services()["users"].get_auth_model(user.id))
            return redirect(url_for(DASHBOARD_HOME))
        except AuthenticationError as exc:
            flash(str(exc), "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Deconnexion reussie", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/users/new", methods=["GET", "POST"])
@login_required
def create_user():
    if current_user.role != UserRole.ADMIN.value:
        flash("Acces reserve a l'administration", "danger")
        return redirect(url_for(DASHBOARD_HOME))

    if request.method == "POST":
        full_name = request.form.get("full_name", "")
        email = request.form.get("email", "")
        role = request.form.get("role", "")
        password = request.form.get("password", "")

        try:
            get_use_cases().register_user.execute(
                actor=current_actor(),
                full_name=full_name,
                email=email,
                role=role,
                plain_password=password,
            )
            flash("Compte cree avec succes", "success")
            return redirect(url_for("auth.create_user"))
        except (ValidationError, AuthorizationError) as exc:
            flash(str(exc), "danger")

    return render_template("auth/create_user.html", roles=UserRole)
