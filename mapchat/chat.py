from flask import app
from flask import Blueprint
from flask import redirect
from flask import render_template
from flask import request

from mapchat.agent.agent import Agent
from .db import get_db

app.secret_key = 0x8ada3717b2b22cdc54e69a97d42b6ea5a48e077ec63afde8eb802ddc07f2b4fb

bp = Blueprint("chat", __name__)


@bp.route("/", methods=("GET", "POST"))
def chat():
    """Allows user to type a prompt for evaluation by the LLM."""
    agent = Agent(get_db())
    message_history = agent.chat(
        request.form["prompt"]
    ) if (request.method == "POST" and len(request.form["prompt"]) > 0 else agent.message_history()
    return render_template("chat/chat.html", messages=message_history)


@bp.route("/clear/", methods=["POST"])
def clear():
    Agent(get_db()).clear_message_history()
    return redirect("/")
