import functools

from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

from .db import get_db

bp = Blueprint("upload", __name__, url_prefix="/upload")


@bp.route("/uploadlh", methods=("GET", "POST"))
def uploadlh():
    """Uploads location history.

    User specifies a path to a local JSON location history file.
    This upload the contents, validates them, and saves them in
    the database.
    """
    if request.method == "POST":
        pass

    return render_template("upload/uploadlh.html")