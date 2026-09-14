from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.domain.entities.user import UserRole
from app.domain.errors import DomainError
from app.interfaces.web.routes.utils import current_actor, get_use_cases

parent_bp = Blueprint("parent", __name__, url_prefix="/parent")


def _guard_parent():
    actor = current_actor()
    if actor.role != UserRole.PARENT:
        flash("Accès réservé aux parents", "danger")
        return redirect(url_for("dashboard.home"))
    return None


@parent_bp.route("/children", methods=["GET"])
@login_required
def children():
    guard = _guard_parent()
    if guard:
        return guard
    actor = current_actor()
    children = get_use_cases().list_children.execute(actor)
    return render_template("parent/children.html", children=children)


@parent_bp.route("/children/<int:child_id>/channels", methods=["GET"])
@login_required
def child_channels(child_id: int):
    guard = _guard_parent()
    if guard:
        return guard
    actor = current_actor()
    children = get_use_cases().list_children.execute(actor)
    child = next((c for c in children if c.id == child_id), None)
    if child is None:
        flash("Enfant introuvable", "danger")
        return redirect(url_for("parent.children"))

    # Get channels for this child's class
    use_cases = get_use_cases()
    # Find channels matching the child's class name
    all_channels = use_cases.list_user_channels.execute(actor)
    class_channels = [c for c in all_channels if c.name == child.class_name]

    return render_template(
        "parent/child_channels.html",
        child=child,
        channels=class_channels,
    )