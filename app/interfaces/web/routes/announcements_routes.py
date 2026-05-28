import os
from uuid import uuid4

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.domain.errors import AuthorizationError, ValidationError
from app.interfaces.web.routes.utils import current_actor, get_use_cases

announcements_bp = Blueprint("announcements", __name__, url_prefix="/announcements")


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
            upload.save(os.path.join(current_app.config["UPLOAD_FOLDER"], pdf_filename))

        try:
            get_use_cases().create_announcement.execute(
                actor=current_actor(),
                title=title,
                content=content,
                pdf_filename=pdf_filename,
            )
            flash("Annonce publiee", "success")
            return redirect(url_for("announcements.list_announcements"))
        except (ValidationError, AuthorizationError) as exc:
            flash(str(exc), "danger")

    return render_template("announcements/create.html")
