import json
import requests
from typing import Any, Dict, List, Optional
from mapchat.backends.llm_backend import LLMBackendProtocol


class OllamaBackend(LLMBackendProtocol):

    def __init__(self):
        pass

    def chat(self,
             prompt: str,
             prev_messages: List[Dict[str, str]],
             tools: List[Dict[str, Any]] = [],
             model: str = "llama3.1") -> Dict[str, str]:
        """
        Simple helper for querying a local ollama instance. It is expected that the
        instance is running on port 11434. "role" field in the request is always set
        to "user". Code mostly copied from ollama python-simplechat example.

        Args:
            prompt (str): User-entered prompt to send for inference.
            prev_messages (List[Dict[str, str]]): Previous chat history between the
                user and the model. Each list item is a message with "role" and
                "content" keys populated.
            tools (List[Dict[str, Any]]): List of tools to pass to Ollama. See
                https://github.com/ollama/ollama/blob/main/docs/api.md#chat-request-with-tools
            model (str, optional): Model to use for inference. Defaults to
                "llama3.1".

        Raises:
            Exception: Raises exception when there is an error returned by ollama.

        Returns:
            Dict[str, str]: Returns the inferred response from ollama with the role
                set to assistant.
        """
        messages = prev_messages + [{"role": "user", "content": prompt}]
        input_json = {"model": model, "messages": messages, "stream": True}
        if len(tools) > 0:
            input_json["tools"] = tools
        r = requests.post("http://localhost:11434/api/chat",
                          json=input_json,
                          stream=True)
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

        return {"role": "assistant", "content": output}
