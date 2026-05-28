from flask import Blueprint, render_template
from flask_login import login_required

from app.interfaces.web.routes.utils import current_actor, get_use_cases

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/")


@dashboard_bp.route("/", methods=["GET"])
@login_required
def home():
    data = get_use_cases().get_dashboard.execute(current_actor())
    return render_template("dashboard/home.html", data=data)
