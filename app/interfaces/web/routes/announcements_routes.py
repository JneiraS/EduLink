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


@announcements_bp.route("/", methods=["GET"])
@login_required
def list_announcements():
    announcements = get_use_cases().list_announcements.execute()
    return render_template("announcements/list.html", announcements=announcements)


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
    if request.method == "POST":
        title = request.form.get("title", "")
        content = request.form.get("content", "")
        upload = request.files.get("document")
        pdf_filename = None

        if upload and upload.filename:
            if not _allowed_file(upload.filename):
                flash("Seuls les PDF sont autorises", "danger")
                return redirect(url_for("announcements.create_announcement"))

            original = secure_filename(upload.filename)
            pdf_filename = f"{uuid4().hex}_{original}"
            upload.save(os.path.join(_uploads_dir(), pdf_filename))

        try:
            get_use_cases().create_announcement.execute(
                actor=current_actor(),
                title=title,
                content=content,
                pdf_filename=pdf_filename,
            )
        except Exception:
            if pdf_filename:
                os.remove(os.path.join(_uploads_dir(), pdf_filename))
            raise

        flash("Annonce publiee", "success")
        return redirect(url_for("announcements.list_announcements"))

    return render_template("announcements/create.html")
