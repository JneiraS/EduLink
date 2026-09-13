from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.domain.entities.user import UserRole
from app.domain.errors import DomainError
from app.interfaces.web.routes.utils import current_actor, get_use_cases

calendar_bp = Blueprint("calendar", __name__, url_prefix="/calendar")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@calendar_bp.route("/", methods=["GET"])
@login_required
def index():
    actor = current_actor()
    use_cases = get_use_cases()

    selected_type = (request.args.get("type") or "all").strip() or "all"
    selected_class = (request.args.get("class_name") or "all").strip() or "all"
    selected_category = (request.args.get("category") or "all").strip() or "all"

    all_events = use_cases.list_calendar_events.execute(actor=actor)
    class_names = sorted(
        {event.class_name for event in all_events}
        | set(use_cases.list_class_names.execute())
    )

    events = use_cases.list_calendar_events.execute(
        actor=actor,
        type_filter=selected_type,
        class_name=selected_class,
        category=selected_category,
    )

    now = datetime.now()
    next_deadline = next(
        (event for event in events if event.type.value == "deadline"), None
    )
    days_to_deadline = None
    if next_deadline is not None:
        days_to_deadline = max(
            (next_deadline.start_date.date() - now.date()).days, 0
        )

    september_count = sum(
        1 for event in events if event.start_date.month == 9
    )
    next_holiday = next(
        (event for event in events if event.type.value == "holiday"), None
    )

    return render_template(
        "calendar/index.html",
        events=events,
        class_names=class_names,
        selected_type=selected_type,
        selected_class=selected_class,
        selected_category=selected_category,
        can_manage=actor.role in (UserRole.ADMIN, UserRole.TEACHER),
        next_deadline=next_deadline,
        days_to_deadline=days_to_deadline,
        september_count=september_count,
        next_holiday=next_holiday,
        today=now.date(),
    )


@calendar_bp.route("/events", methods=["POST"])
@login_required
def create_event():
    actor = current_actor()
    start_date = _parse_datetime(request.form.get("start_date"))
    end_date = _parse_datetime(request.form.get("end_date"))
    if start_date is None:
        flash("La date de début est requise", "danger")
        return redirect(url_for("calendar.index"))

    try:
        get_use_cases().create_calendar_event.execute(
            actor=actor,
            title=request.form.get("title", ""),
            type_value=request.form.get("type", "event"),
            start_date=start_date,
            end_date=end_date,
            category=request.form.get("category"),
            class_name=request.form.get("class_name"),
            description=request.form.get("description"),
            location=request.form.get("location"),
            priority=request.form.get("priority"),
        )
    except DomainError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("calendar.index"))

    flash("Date ajoutée au calendrier", "success")
    return redirect(url_for("calendar.index"))


@calendar_bp.route("/events/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id: int):
    try:
        get_use_cases().delete_calendar_event.execute(current_actor(), event_id)
        flash("Date supprimée du calendrier", "success")
    except DomainError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("calendar.index"))