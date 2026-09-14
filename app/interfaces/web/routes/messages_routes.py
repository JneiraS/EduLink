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
            flash("Canal créé", "success")
            return redirect(url_for(MESSAGES_CHANNELS))
        except (ValidationError, AuthorizationError) as exc:
            flash(str(exc), "danger")

    channels_data = get_use_cases().list_user_channels.execute(actor)
    direct_channels = [c for c in channels_data if c.kind == "direct"]
    group_channels = [c for c in channels_data if c.kind != "direct"]

    target_channel_id = request.args.get("channel_id", type=int)
    if target_channel_id and any(
        channel.id == target_channel_id for channel in channels_data
    ):
        return redirect(url_for(CHANNEL_DETAIL, channel_id=target_channel_id))

    notif_settings = get_use_cases().get_notification_settings.execute(actor)
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
        notif_global_enabled=notif_settings["global_enabled"],
        notif_channel_states=notif_settings["channel_states"],
    )


@messages_bp.route("/channels/<int:channel_id>/notifications", methods=["POST"])
@login_required
def toggle_channel_notifications(channel_id: int):
    actor = current_actor()
    try:
        enabled = get_use_cases().toggle_channel_notifications.execute(
            actor, channel_id
        )
        flash(
            "Notifications activées" if enabled else "Notifications désactivées",
            "success",
        )
    except (NotFoundError, AuthorizationError) as exc:
        flash(str(exc), "danger")
    return redirect(url_for(MESSAGES_CHANNELS))


@messages_bp.route("/notifications/global", methods=["POST"])
@login_required
def set_global_notifications():
    enabled = request.form.get("enabled") == "1"
    get_use_cases().set_global_notifications.execute(current_actor(), enabled)
    flash(
        "Notifications globales activées"
        if enabled
        else "Notifications globales désactivées",
        "success",
    )
    return redirect(url_for(MESSAGES_CHANNELS))


@messages_bp.route("/new-conversation", methods=["GET", "POST"])
@login_required
def new_conversation():
    actor = current_actor()
    if request.method == "POST":
        member_id = request.form.get("member", "")
        if not member_id.isdigit():
            flash("Sélectionnez un contact", "danger")
            return redirect(url_for("messages.new_conversation"))

        try:
            channel = get_use_cases().open_direct_conversation.execute(
                actor, other_user_id=int(member_id)
            )
            flash("Conversation créée", "success")
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


@messages_bp.route("/find-parent", methods=["GET", "POST"])
@login_required
def find_parent():
    actor = current_actor()
    if actor.role not in (UserRole.ADMIN, UserRole.TEACHER):
        flash("Accès réservé aux enseignants", "danger")
        return redirect(url_for("dashboard.home"))
    if request.method == "POST":
        parent_id = request.form.get("parent_id", type=int)
        if parent_id:
            try:
                channel = get_use_cases().open_direct_conversation.execute(
                    actor, other_user_id=parent_id
                )
                flash("Conversation créée", "success")
                return redirect(url_for(CHANNEL_DETAIL, channel_id=channel.id))
            except (ValidationError, NotFoundError) as exc:
                flash(str(exc), "danger")
        return redirect(url_for("messages.find_parent"))

    query = request.args.get("q", type=str, default="")
    results = []
    if query.strip():
        try:
            results = get_use_cases().find_parents_by_child.execute(
                actor, query=query
            )
        except (AuthorizationError, ValidationError) as exc:
            flash(str(exc), "danger")
    return render_template(
        "messages/find_parent.html",
        results=results,
        search_query=query,
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
            flash("Modèle créé", "success")
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
        flash("Modèle supprimé", "success")
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
        flash("Modèle introuvable", "danger")
        return redirect(url_for("messages.templates"))

    if request.method == "POST":
        label = request.form.get("label", "")
        content = request.form.get("content", "")
        try:
            get_use_cases().update_message_template.execute(
                actor, template_id, label=label, content=content
            )
            flash("Modèle mis à jour", "success")
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
                flash("Membres ajoutés", "success")
            except (ValidationError, AuthorizationError, NotFoundError) as exc:
                flash(str(exc), "danger")

            return redirect(url_for(CHANNEL_DETAIL, channel_id=channel_id))
        if action == "toggle_pin":
            message_id = request.form.get("message_id", type=int)
            pinned = request.form.get("pinned") == "1"
            try:
                get_use_cases().pin_message.execute(
                    actor,
                    channel_id=channel_id,
                    message_id=message_id or 0,
                    pinned=pinned,
                )
                flash("Message épinglé" if pinned else "Message désépinglé", "success")
            except (ValidationError, AuthorizationError, NotFoundError) as exc:
                flash(str(exc), "danger")

            return redirect(url_for(CHANNEL_DETAIL, channel_id=channel_id))
        if action == "toggle_notifications":
            try:
                enabled = get_use_cases().toggle_channel_notifications.execute(
                    actor, channel_id
                )
                flash(
                    "Notifications activées"
                    if enabled
                    else "Notifications désactivées",
                    "success",
                )
            except (NotFoundError, AuthorizationError) as exc:
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

    use_cases = get_use_cases()
    search_query = request.args.get("q", type=str)

    try:
        user_channels = use_cases.list_user_channels.execute(actor)
        channel_members = use_cases.list_channel_members.execute(
            actor, channel_id=channel_id
        )
        use_cases.mark_channel_notifications_read.execute(
            actor, channel_id=channel_id
        )
        channel_name = resolve_channel_name(channel_id, user_channels)
        channel_obj = next(
            (channel for channel in user_channels if channel.id == channel_id),
            None,
        )
        is_direct = bool(channel_obj and channel_obj.kind == "direct")
        current_member_ids = {member.id for member in channel_members}
        all_users = sorted(
            use_cases.list_all_users.execute(),
            key=lambda u: u.full_name.casefold(),
        )
        available_users = [
            user for user in all_users if user.id not in current_member_ids
        ]
        can_manage_members = actor.role in {UserRole.ADMIN, UserRole.TEACHER}
        message_templates = use_cases.list_message_templates.execute(actor)
        notif_settings = use_cases.get_notification_settings.execute(actor)
        notifications_enabled = notif_settings["channel_states"].get(channel_id, True)

        if search_query is not None and search_query.strip():
            messages = use_cases.search_channel_messages.execute(
                actor, channel_id=channel_id, query=search_query
            )
            has_older = False
            search_mode = True
        else:
            before_id = request.args.get("before", type=int)
            messages, has_older = use_cases.list_channel_messages.execute(
                actor, channel_id=channel_id, before_id=before_id
            )
            search_mode = False

        member_names = build_member_name_index(
            channel_members,
            messages,
            users_lookup=lambda sender_ids: use_cases
            .find_users_by_ids.execute(list(sender_ids)),
        )
        messages_view = build_messages_view(messages, member_names)
        oldest_message_id = messages[0].id if messages else None

        if not is_direct:
            pinned_messages = use_cases.list_pinned_messages.execute(
                actor, channel_id=channel_id
            )
            pinned_member_names = build_member_name_index(
                channel_members,
                pinned_messages,
                users_lookup=lambda sender_ids: use_cases
                .find_users_by_ids.execute(list(sender_ids)),
            )
            pinned_view = build_messages_view(pinned_messages, pinned_member_names)
        else:
            pinned_view = []
    except (AuthorizationError, NotFoundError) as exc:
        flash(str(exc), "danger")
        return redirect(url_for(MESSAGES_CHANNELS))

    return render_template(
        "messages/channel_detail.html",
        channel_id=channel_id,
        channel_name=channel_name,
        messages=messages_view,
        pinned_messages=pinned_view,
        members=channel_members,
        available_users_by_role=group_users_by_role(available_users),
        can_manage_members=can_manage_members,
        is_direct=is_direct,
        message_templates=message_templates,
        has_older=has_older,
        oldest_message_id=oldest_message_id,
        search_mode=search_mode,
        search_query=search_query,
        notifications_enabled=notifications_enabled,
    )
