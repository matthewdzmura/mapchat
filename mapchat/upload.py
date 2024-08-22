import functools

from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

import json

from .db import get_db
from mapchat.backends.location_history_backend import LocationHistoryBackend

bp = Blueprint("upload", __name__, url_prefix="/upload")


@bp.route("/uploadlh", methods=("GET", "POST"))
def upload_location_history():
    """Uploads location history.

    User specifies a path to a local JSON location history file.
    This upload the contents, validates them, and saves them in
    the database.
    """
    if request.method == "POST":
        f = request.files['file']
        lh = json.loads(f.read())
        backend = LocationHistoryBackend(get_db());
        backend.populate_location_history(lh);
        flash("Successfully uploaded Location History data.")
        return redirect("/")

    return render_template("upload/uploadlh.html")