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
        member_names = {}
        for member in channel_members:
            member_names[member.id] = member.full_name
            member_names[str(member.id)] = member.full_name

        # Resolve names for historical messages even if sender is no longer listed as channel member.
        sender_ids = {m.sender_id for m in channel_messages}
        if sender_ids:
            known_users = UserModel.query.filter(UserModel.id.in_(sender_ids)).all()
            for user in known_users:
                member_names[user.id] = user.full_name
                member_names[str(user.id)] = user.full_name

        messages_view = []
        for message in channel_messages:
            sender_key = message.sender_id
            try:
                sender_key_int = int(sender_key)
            except (TypeError, ValueError):
                sender_key_int = None

            sender_name = (
                member_names.get(sender_key)
                or member_names.get(str(sender_key))
                or (
                    member_names.get(sender_key_int)
                    if sender_key_int is not None
                    else None
                )
                or f"Utilisateur {sender_key}"
            )

            messages_view.append(
                {
                    "sender_name": sender_name,
                    "created_at": message.created_at,
                    "content": message.content,
                }
            )
    except (AuthorizationError, NotFoundError) as exc:
        flash(str(exc), "danger")
        return redirect(url_for(MESSAGES_CHANNELS))

    return render_template(
        "messages/channel_detail.html",
        channel_id=channel_id,
        messages=messages_view,
        members=channel_members,
        member_names=member_names,
    )
