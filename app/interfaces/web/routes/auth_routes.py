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

    invitation_url = None
    if request.method == "POST":
        full_name = request.form.get("full_name", "")
        email = request.form.get("email", "")
        role = request.form.get("role", "")

        try:
            _, invitation = get_use_cases().create_user_with_invitation.execute(
                actor=current_actor(),
                full_name=full_name,
                email=email,
                role=role,
            )
            flash("Compte cree avec succes", "success")
            invitation_url = url_for(
                "auth.invite", token=invitation.token, _external=True
            )
        except (ValidationError, AuthorizationError) as exc:
            flash(str(exc), "danger")

    return render_template(
        "auth/create_user.html",
        roles=UserRole,
        invitation_url=invitation_url,
    )


@auth_bp.route("/invite/<token>", methods=["GET", "POST"])
def invite(token: str):
    if current_user.is_authenticated:
        return redirect(url_for(DASHBOARD_HOME))

    try:
        user = get_use_cases().validate_invitation.execute(token)
    except AuthenticationError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if password != confirm:
            flash("Passwords do not match", "danger")
            return render_template("auth/set_password.html", user=user, token=token)
        try:
            accepted = get_use_cases().accept_invitation.execute(token, password)
            login_user(get_services()["users"].get_auth_model(accepted.id))
            flash("Mot de passe defini, bienvenue !", "success")
            return redirect(url_for(DASHBOARD_HOME))
        except AuthenticationError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("auth.login"))
        except ValidationError as exc:
            flash(str(exc), "danger")
            return render_template("auth/set_password.html", user=user, token=token)

    return render_template("auth/set_password.html", user=user, token=token)
