from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.domain.entities.user import UserRole
from app.domain.errors import AuthorizationError, NotFoundError, ValidationError
from app.interfaces.web.routes.presentation import (
    build_member_name_index,
    build_messages_view,
    group_users_by_role,
    parse_member_ids,
    resolve_channel_name,
)
from app.interfaces.web.routes.utils import current_actor, get_use_cases

messages_bp = Blueprint("messages", __name__, url_prefix="/messages")
MESSAGES_CHANNELS = "messages.channels"
CHANNEL_DETAIL = "messages.channel_detail"


@messages_bp.route("/channels", methods=["GET", "POST"])
@login_required
def channels():
    member_ids: list[int] = []
    form_name = ""
    if request.method == "POST":
        name = request.form.get("name", "")
        form_name = name
        member_ids = parse_member_ids(request.form)

        try:
            get_use_cases().create_channel.execute(
                current_actor(), name=name, members=member_ids
            )
            flash("Canal cree", "success")
            return redirect(url_for(MESSAGES_CHANNELS))
        except (ValidationError, AuthorizationError) as exc:
            flash(str(exc), "danger")

    channels_data = get_use_cases().list_user_channels.execute(current_actor())
    users = sorted(
        get_use_cases().list_all_users.execute(),
        key=lambda u: u.full_name.casefold(),
    )
    return render_template(
        "messages/channels.html",
        channels=channels_data,
        users_by_role=group_users_by_role(users),
        selected_member_ids=member_ids,
        form_name=form_name,
        current_user_id=current_user.id,
    )


@messages_bp.route("/channels/<int:channel_id>", methods=["GET", "POST"])
@login_required
def channel_detail(channel_id: int):
    actor = current_actor()

    if request.method == "POST":
        action = request.form.get("action", "send_message")

        if action == "add_members":
            member_ids = parse_member_ids(request.form)

            try:
                get_use_cases().add_channel_members.execute(
                    actor, channel_id=channel_id, members=member_ids
                )
                flash("Membres ajoutes", "success")
            except (ValidationError, AuthorizationError, NotFoundError) as exc:
                flash(str(exc), "danger")

            return redirect(url_for(CHANNEL_DETAIL, channel_id=channel_id))

        content = request.form.get("content", "")
        try:
            get_use_cases().send_message.execute(
                actor, channel_id=channel_id, content=content
            )
            return redirect(url_for(CHANNEL_DETAIL, channel_id=channel_id))
        except (ValidationError, AuthorizationError, NotFoundError) as exc:
            flash(str(exc), "danger")
            return redirect(url_for(MESSAGES_CHANNELS))

    try:
        before_id = request.args.get("before", type=int)
        channel_messages, has_older = get_use_cases().list_channel_messages.execute(
            actor, channel_id=channel_id, before_id=before_id
        )
        user_channels = get_use_cases().list_user_channels.execute(actor)
        channel_members = get_use_cases().list_channel_members.execute(
            actor, channel_id=channel_id
        )
        channel_name = resolve_channel_name(channel_id, user_channels)
        member_names = build_member_name_index(
            channel_members,
            channel_messages,
            users_lookup=lambda sender_ids: get_use_cases()
            .find_users_by_ids.execute(list(sender_ids)),
        )
        messages_view = build_messages_view(channel_messages, member_names)

        current_member_ids = {member.id for member in channel_members}
        all_users = sorted(
            get_use_cases().list_all_users.execute(),
            key=lambda u: u.full_name.casefold(),
        )
        available_users = [
            user for user in all_users if user.id not in current_member_ids
        ]
        can_manage_members = actor.role in {UserRole.ADMIN, UserRole.TEACHER}
    except (AuthorizationError, NotFoundError) as exc:
        flash(str(exc), "danger")
        return redirect(url_for(MESSAGES_CHANNELS))

    return render_template(
        "messages/channel_detail.html",
        channel_id=channel_id,
        channel_name=channel_name,
        messages=messages_view,
        members=channel_members,
        available_users_by_role=group_users_by_role(available_users),
        can_manage_members=can_manage_members,
        has_older=has_older,
        oldest_message_id=channel_messages[0].id if channel_messages else None,
    )
