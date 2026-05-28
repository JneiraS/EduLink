from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.domain.errors import AuthorizationError, NotFoundError, ValidationError
from app.infrastructure.database.models import UserModel
from app.interfaces.web.routes.utils import current_actor, get_use_cases

messages_bp = Blueprint("messages", __name__, url_prefix="/messages")
MESSAGES_CHANNELS = "messages.channels"


@messages_bp.route("/channels", methods=["GET", "POST"])
@login_required
def channels():
    if request.method == "POST":
        name = request.form.get("name", "")
        raw_members = request.form.getlist("members") + request.form.getlist(
            "members[]"
        )
        member_ids = sorted({int(x) for x in raw_members if x.isdigit()})

        try:
            get_use_cases().create_channel.execute(
                current_actor(), name=name, members=member_ids
            )
            flash("Canal cree", "success")
            return redirect(url_for(MESSAGES_CHANNELS))
        except (ValidationError, AuthorizationError) as exc:
            flash(str(exc), "danger")

    channels_data = get_use_cases().list_user_channels.execute(current_actor())
    users = UserModel.query.order_by(UserModel.full_name.asc()).all()
    return render_template(
        "messages/channels.html",
        channels=channels_data,
        users=users,
        current_user_id=current_user.id,
    )


@messages_bp.route("/channels/<int:channel_id>", methods=["GET", "POST"])
@login_required
def channel_detail(channel_id: int):
    if request.method == "POST":
        content = request.form.get("content", "")
        try:
            get_use_cases().send_message.execute(
                current_actor(), channel_id=channel_id, content=content
            )
            return redirect(url_for("messages.channel_detail", channel_id=channel_id))
        except (ValidationError, AuthorizationError, NotFoundError) as exc:
            flash(str(exc), "danger")
            return redirect(url_for(MESSAGES_CHANNELS))

    try:
        channel_messages = get_use_cases().list_channel_messages.execute(
            current_actor(), channel_id=channel_id
        )
        channel_members = get_use_cases().list_channel_members.execute(
            current_actor(), channel_id=channel_id
        )
    except (AuthorizationError, NotFoundError) as exc:
        flash(str(exc), "danger")
        return redirect(url_for(MESSAGES_CHANNELS))

    return render_template(
        "messages/channel_detail.html",
        channel_id=channel_id,
        messages=channel_messages,
        members=channel_members,
    )
