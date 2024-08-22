from flask import app
from flask import Blueprint
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
import json
from werkzeug.exceptions import abort

from mapchat.agent.agent import Agent
from mapchat.backends.chat_history_backend import ChatHistoryBackend
from mapchat.backends.ollama_backend import ollama_chat
from .db import get_db

app.secret_key = 0x8ada3717b2b22cdc54e69a97d42b6ea5a48e077ec63afde8eb802ddc07f2b4fb

bp = Blueprint("chat", __name__)

@bp.route("/", methods=("GET", "POST"))
def chat():
    """Allows user to type a prompt for evaluation by the LLM."""
    chat_backend = ChatHistoryBackend(get_db())
    message_history = chat_backend.fetch_history()

    if request.method == "POST":
        prompt = request.form["prompt"]
        agent = Agent()
        chat_backend.append_chat("user", prompt)
        response = agent.chat(message_history, prompt)
        message_history = message_history + [{"role": "user", "content": prompt}, response]
        chat_backend.append_chat(response['role'], response['content'])
    return render_template("chat/chat.html", messages=message_history)

@bp.route("/clear/", methods=["POST"])
def clear():
    ChatHistoryBackend(get_db()).clear_history()
    return redirect("/")