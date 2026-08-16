import os
from uuid import uuid4

from flask import (
    abort,
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.domain.errors import NotFoundError
from app.interfaces.web.routes.utils import current_actor, get_use_cases

announcements_bp = Blueprint("announcements", __name__, url_prefix="/announcements")


def _uploads_dir() -> str:
    # Resolve uploads path from project root so it stays stable regardless of launch cwd.
    return os.path.abspath(
        os.path.join(current_app.root_path, "..", current_app.config["UPLOAD_FOLDER"])
    )


def _allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_EXTENSIONS"]
    )


def _is_pdf_content(upload) -> bool:
    upload.seek(0)
    header = upload.read(4)
    upload.seek(0)
    return header == b"%PDF"


@announcements_bp.route("/", methods=["GET"])
@login_required
def list_announcements():
    page = max(request.args.get("page", 1, type=int), 1)
    announcements, total = get_use_cases().list_announcements.execute(page=page)
    total_pages = max((total + 9) // 10, 1)
    read_status = get_use_cases().get_announcement_read_status.execute(
        current_actor(), announcements
    )
    return render_template(
        "announcements/list.html",
        announcements=announcements,
        read_status=read_status,
        page=page,
        total_pages=total_pages,
    )


@announcements_bp.route("/<int:announcement_id>/confirm-read", methods=["POST"])
@login_required
def confirm_read(announcement_id: int):
    try:
        get_use_cases().confirm_announcement_read.execute(
            current_actor(), announcement_id
        )
        flash("Lecture confirmee", "success")
    except NotFoundError as exc:
        flash(str(exc), "danger")
    page = max(request.args.get("page", 1, type=int), 1)
    return redirect(url_for("announcements.list_announcements", page=page))


@announcements_bp.route("/files/<path:filename>", methods=["GET"])
@login_required
def download_announcement_pdf(filename: str):
    safe_name = secure_filename(filename)
    if safe_name != filename or not _allowed_file(safe_name):
        abort(404)
    return send_from_directory(_uploads_dir(), safe_name, as_attachment=True)


@announcements_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_announcement():
    actor = current_actor()
    channels = get_use_cases().list_user_channels.execute(actor)

    if request.method == "POST":
        title = request.form.get("title", "")
        content = request.form.get("content", "")
        upload = request.files.get("document")
        pdf_filename = None

        audience = request.form.get("audience", "all")
        if audience == "channels":
            target_channel_ids = sorted(
                {int(value) for value in request.form.getlist("target_channels") if value.isdigit()}
            )
            if not target_channel_ids:
                flash("Selectionnez au moins un canal", "danger")
                return redirect(url_for("announcements.create_announcement"))
        else:
            target_channel_ids = []

        if upload and upload.filename:
            if not _allowed_file(upload.filename):
                flash("Seuls les PDF sont autorises", "danger")
                return redirect(url_for("announcements.create_announcement"))
            if not _is_pdf_content(upload):
                flash("Seuls les PDF sont autorises", "danger")
                return redirect(url_for("announcements.create_announcement"))

            original = secure_filename(upload.filename)
            pdf_filename = f"{uuid4().hex}_{original}"
            upload.save(os.path.join(_uploads_dir(), pdf_filename))

        try:
            get_use_cases().create_announcement.execute(
                actor=actor,
                title=title,
                content=content,
                pdf_filename=pdf_filename,
                target_channel_ids=target_channel_ids,
            )
        except Exception:
            if pdf_filename:
                os.remove(os.path.join(_uploads_dir(), pdf_filename))
            raise

        flash("Annonce publiee", "success")
        return redirect(url_for("announcements.list_announcements"))

    return render_template("announcements/create.html", channels=channels)
