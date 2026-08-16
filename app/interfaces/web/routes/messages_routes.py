from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.domain.entities.message_template import MessageTemplate
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
    actor = current_actor()
    can_manage = actor.role in {UserRole.ADMIN, UserRole.TEACHER}
    member_ids: list[int] = []
    form_name = ""
    if request.method == "POST":
        name = request.form.get("name", "")
        form_name = name
        member_ids = parse_member_ids(request.form)

        try:
            get_use_cases().create_channel.execute(actor, name=name, members=member_ids)
            flash("Canal cree", "success")
            return redirect(url_for(MESSAGES_CHANNELS))
        except (ValidationError, AuthorizationError) as exc:
            flash(str(exc), "danger")

    channels_data = get_use_cases().list_user_channels.execute(actor)
    direct_channels = [c for c in channels_data if c.kind == "direct"]
    group_channels = [c for c in channels_data if c.kind != "direct"]
    users = sorted(
        get_use_cases().list_all_users.execute(),
        key=lambda u: u.full_name.casefold(),
    )
    return render_template(
        "messages/channels.html",
        channels=channels_data,
        direct_channels=direct_channels,
        group_channels=group_channels,
        users_by_role=group_users_by_role(users),
        selected_member_ids=member_ids,
        form_name=form_name,
        current_user_id=current_user.id,
        can_manage=can_manage,
    )


@messages_bp.route("/new-conversation", methods=["GET", "POST"])
@login_required
def new_conversation():
    actor = current_actor()
    if request.method == "POST":
        member_id = request.form.get("member", "")
        if not member_id.isdigit():
            flash("Selectionnez un contact", "danger")
            return redirect(url_for("messages.new_conversation"))

        try:
            channel = get_use_cases().open_direct_conversation.execute(
                actor, other_user_id=int(member_id)
            )
            flash("Conversation creee", "success")
            return redirect(url_for(CHANNEL_DETAIL, channel_id=channel.id))
        except (ValidationError, NotFoundError) as exc:
            flash(str(exc), "danger")
            return redirect(url_for("messages.new_conversation"))

    users = sorted(
        get_use_cases().list_all_users.execute(),
        key=lambda u: u.full_name.casefold(),
    )
    contacts = [user for user in users if user.id != (actor.id or 0)]
    return render_template(
        "messages/new_conversation.html",
        users_by_role=group_users_by_role(contacts),
        current_user_id=current_user.id,
    )


@messages_bp.route("/templates", methods=["GET", "POST"])
@login_required
def templates():
    actor = current_actor()
    if request.method == "POST":
        label = request.form.get("label", "")
        content = request.form.get("content", "")
        try:
            get_use_cases().create_message_template.execute(
                actor, label=label, content=content
            )
            flash("Modele cree", "success")
            return redirect(url_for("messages.templates"))
        except ValidationError as exc:
            flash(str(exc), "danger")

    my_templates = get_use_cases().list_message_templates.execute(actor)
    return render_template("messages/templates.html", templates=my_templates)


@messages_bp.route("/templates/<int:template_id>/delete", methods=["POST"])
@login_required
def delete_template(template_id: int):
    try:
        get_use_cases().delete_message_template.execute(
            current_actor(), template_id
        )
        flash("Modele supprime", "success")
    except AuthorizationError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("messages.templates"))


@messages_bp.route("/templates/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
def edit_template(template_id: int):
    actor = current_actor()
    my_templates = get_use_cases().list_message_templates.execute(actor)
    template = next(
        (t for t in my_templates if t.id == template_id), None
    )
    if template is None:
        flash("Template not found", "danger")
        return redirect(url_for("messages.templates"))

    if request.method == "POST":
        label = request.form.get("label", "")
        content = request.form.get("content", "")
        try:
            get_use_cases().update_message_template.execute(
                actor, template_id, label=label, content=content
            )
            flash("Modele mis a jour", "success")
            return redirect(url_for("messages.templates"))
        except ValidationError as exc:
            flash(str(exc), "danger")
            template = MessageTemplate(
                id=template_id,
                owner_id=actor.id or 0,
                label=label,
                content=content,
            )

    return render_template("messages/edit_template.html", template=template)


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
        channel_obj = next(
            (channel for channel in user_channels if channel.id == channel_id), None
        )
        is_direct = bool(channel_obj and channel_obj.kind == "direct")
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
        message_templates = get_use_cases().list_message_templates.execute(actor)
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
        is_direct=is_direct,
        message_templates=message_templates,
        has_older=has_older,
        oldest_message_id=channel_messages[0].id if channel_messages else None,
    )
