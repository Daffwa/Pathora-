from flask import Blueprint, render_template


bp = Blueprint("public", __name__)

@bp.route("/", endpoint="index")
def index():
    return render_template("index.html")
