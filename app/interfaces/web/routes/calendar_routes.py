from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.domain.entities.user import UserRole
from app.domain.errors import DomainError
from app.interfaces.web.routes.utils import current_actor, get_use_cases

calendar_bp = Blueprint("calendar", __name__, url_prefix="/calendar")

FRENCH_MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]
FRENCH_MONTHS_ABBR = [
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]
FRENCH_DAYS_ABBR = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    month_index = year * 12 + (month - 1) + delta
    return month_index // 12, month_index % 12 + 1


def _month_key(value: date) -> tuple[int, int]:
    return value.year, value.month


def _month_bounds(events, today: date) -> tuple[tuple[int, int], tuple[int, int]]:
    months = {_month_key(event.start_date) for event in events}
    first = last = _month_key(today)
    if months:
        first = min(months)
        last = max(months)
    return min(first, _month_key(today)), max(last, _month_key(today))


def _parse_month(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m").date()
    except ValueError:
        return None
    return parsed.year, parsed.month


def _build_week_rows(
    year: int, month: int, events_by_day: dict, today: date
) -> list[list[dict | None]]:
    first_weekday = date(year, month, 1).weekday()
    month_length = monthrange(year, month)[1]
    cells: list[dict | None] = [None] * first_weekday
    for day in range(1, month_length + 1):
        day_events = events_by_day.get((year, month, day), [])
        cells.append(
            {
                "day": day,
                "is_today": today == date(year, month, day),
                "events": day_events,
                "extra": max(len(day_events) - 2, 0),
            }
        )
    while len(cells) % 7 != 0:
        cells.append(None)
    return [cells[i:i + 7] for i in range(0, len(cells), 7)]


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
    today = now.date()
    first_bounds, last_bounds = _month_bounds(all_events, today)
    requested_month = _parse_month(request.args.get("month"))
    grid_year, grid_month = requested_month or _month_key(today)
    grid_year, grid_month = min(max((grid_year, grid_month), first_bounds), last_bounds)

    events_by_day: dict = defaultdict(list)
    for event in events:
        events_by_day[(event.start_date.year, event.start_date.month, event.start_date.day)].append(event)

    month_count = sum(
        1 for event in events
        if (event.start_date.year, event.start_date.month) == (grid_year, grid_month)
    )
    prev_month = _shift_month(grid_year, grid_month, -1)
    next_month = _shift_month(grid_year, grid_month, 1)
    prev_month = prev_month if prev_month >= first_bounds else None
    next_month = next_month if next_month <= last_bounds else None
    prev_month = f"{prev_month[0]:04d}-{prev_month[1]:02d}" if prev_month else None
    next_month = f"{next_month[0]:04d}-{next_month[1]:02d}" if next_month else None

    next_deadline = next(
        (event for event in events if event.type.value == "deadline"), None
    )
    days_to_deadline = None
    if next_deadline is not None:
        days_to_deadline = max(
            (next_deadline.start_date.date() - today).days, 0
        )

    grid_month_label = f"{FRENCH_MONTHS[grid_month - 1]} {grid_year}"
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
        month_count=month_count,
        grid_month_label=grid_month_label,
        grid_month_lower=FRENCH_MONTHS[grid_month - 1].lower(),
        grid_month=grid_month,
        fr_months=FRENCH_MONTHS,
        fr_month_abbr=FRENCH_MONTHS_ABBR,
        fr_day_abbr=FRENCH_DAYS_ABBR,
        prev_month=prev_month,
        next_month=next_month,
        calendar_weeks=_build_week_rows(grid_year, grid_month, events_by_day, today),
        next_holiday=next_holiday,
        today=today,
        default_start=now.replace(hour=18, minute=0, second=0, microsecond=0).isoformat(timespec="minutes"),
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