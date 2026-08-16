import os

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.domain.entities.user import UserRole
from app.domain.errors import DomainError
from app.interfaces.web.routes.announcements_routes import _uploads_dir
from app.interfaces.web.routes.utils import current_actor, get_use_cases

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ADMIN_MEMBERS = "admin.members"


def _guard_admin():
    actor = current_actor()
    if actor.role != UserRole.ADMIN:
        flash("Acces reserve a l'administration", "danger")
        return redirect(url_for("dashboard.home"))
    return None


def _remove_pdf(pdf_filename: str | None) -> None:
    if not pdf_filename:
        return
    try:
        os.remove(os.path.join(_uploads_dir(), pdf_filename))
    except OSError:
        pass


@admin_bp.route("/members", methods=["GET"])
@login_required
def members():
    guard = _guard_admin()
    if guard:
        return guard
    users = get_use_cases().list_users_for_admin.execute(current_actor())
    return render_template("admin/members.html", users=users, roles=UserRole)


@admin_bp.route("/members/<int:user_id>/role", methods=["POST"])
@login_required
def change_role(user_id: int):
    guard = _guard_admin()
    if guard:
        return guard
    try:
        get_use_cases().update_user_role.execute(
            current_actor(), user_id=user_id, role=request.form.get("role", "")
        )
        flash("Role mis a jour", "success")
    except DomainError as exc:
        flash(str(exc), "danger")
    return redirect(url_for(ADMIN_MEMBERS))


@admin_bp.route("/members/<int:user_id>/toggle-active", methods=["POST"])
@login_required
def toggle_active(user_id: int):
    guard = _guard_admin()
    if guard:
        return guard
    try:
        updated = get_use_cases().toggle_user_active.execute(current_actor(), user_id)
        if updated.is_active:
            flash("Compte active", "success")
        else:
            flash("Compte desactive", "success")
    except DomainError as exc:
        flash(str(exc), "danger")
    return redirect(url_for(ADMIN_MEMBERS))


@admin_bp.route("/members/<int:user_id>/invite", methods=["POST"])
@login_required
def invite_user(user_id: int):
    guard = _guard_admin()
    if guard:
        return guard
    try:
        invitation = get_use_cases().create_invitation.execute(
            current_actor(), user_id
        )
        invite_url = url_for("auth.invite", token=invitation.token, _external=True)
        flash(f"Lien invitation : {invite_url}", "success")
    except DomainError as exc:
        flash(str(exc), "danger")
    return redirect(url_for(ADMIN_MEMBERS))


@admin_bp.route("/announcements", methods=["GET"])
@login_required
def announcements():
    guard = _guard_admin()
    if guard:
        return guard
    items = get_use_cases().list_announcements_for_admin.execute(current_actor())
    author_ids = sorted({a.created_by for a in items})
    authors = get_use_cases().find_users_by_ids.execute(author_ids)
    author_names = {u.id: u.full_name for u in authors}
    return render_template(
        "admin/announcements.html",
        announcements=items,
        author_names=author_names,
    )


@admin_bp.route("/announcements/<int:announcement_id>/delete", methods=["POST"])
@login_required
def delete_announcement(announcement_id: int):
    guard = _guard_admin()
    if guard:
        return guard
    try:
        deleted = get_use_cases().delete_announcement.execute(
            current_actor(), announcement_id
        )
        _remove_pdf(deleted.pdf_filename)
        flash("Annonce supprimee", "success")
    except DomainError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.announcements"))


@admin_bp.route("/channels", methods=["GET"])
@login_required
def channels():
    guard = _guard_admin()
    if guard:
        return guard
    rows = get_use_cases().list_channels_for_admin.execute(current_actor())
    return render_template("admin/channels.html", channels=rows)


@admin_bp.route("/channels/<int:channel_id>/delete", methods=["POST"])
@login_required
def delete_channel(channel_id: int):
    guard = _guard_admin()
    if guard:
        return guard
    try:
        get_use_cases().delete_channel.execute(current_actor(), channel_id)
        flash("Canal supprime", "success")
    except DomainError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.channels"))