from flask import app
from flask import Blueprint
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
import json
import requests
from werkzeug.exceptions import abort

from .db import get_db

app.secret_key = 0x8ada3717b2b22cdc54e69a97d42b6ea5a48e077ec63afde8eb802ddc07f2b4fb

bp = Blueprint("chat", __name__)

@bp.route("/", methods=("GET", "POST"))
def chat():
    """Allows user to type a prompt for evaluation by the LLM."""
    messages = []
    if 'messages' in session:
        messages = session['messages']

    if request.method == "POST":
        prompt = request.form["prompt"]
        model = "llama3.1"
        # TODO Fetch messages from previous interactions
        messages = messages + [{
            "role": "user", "content": prompt
        }]
        r = requests.post(
            "http://localhost:11434/api/chat",
            json={"model": model, "messages": messages, "stream": True},
            stream=True
        )
        r.raise_for_status()
        output = ""

        for line in r.iter_lines():
            body = json.loads(line)
            if "error" in body:
                raise Exception(body["error"])
            if body.get("done") is False:
                message = body.get("message", "")
                content = message.get("content", "")
                output += content
                # the response streams one token at a time, print that as we receive it
                print(content, end="", flush=True)

            if body.get("done", False):
                message["content"] = output

        messages = messages + [{"role": "assistant", "content": output}]
    session['messages'] = messages
    return render_template("chat/chat.html", messages=messages)

@bp.route("/clear/", methods=["POST"])
def clear():
    if 'messages' in session:
        session.pop('messages', None)
    return redirect("/")