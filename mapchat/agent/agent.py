from mapchat.backends.chat_history_backend import ChatHistoryBackend
from mapchat.backends.location_history_backend import LocationHistoryBackend
from mapchat.backends.llm_backend import LLMBackendProtocol
from mapchat.backends.ollama_backend import OllamaBackend

import sqlite3
from typing import Dict, List


class Agent:
    """ Dummy Agent class. """

    def __init__(self,
                 db: sqlite3.Connection,
                 llm_backend: LLMBackendProtocol = None):
        self._location_history_backend = LocationHistoryBackend(db)
        self._chat_history_backend = ChatHistoryBackend(db)
        self._llm_backend = OllamaBackend(
        ) if llm_backend is None else llm_backend

    def message_history(self) -> List[Dict[str, str]]:
        """
        Fetches the chat history from the backing database using the
        connection.

        Returns:
            List[Dict[str, str]]: Message history where each entry in the
                returned list is a message with keys 'role' and 'content'.
        """
        return self._chat_history_backend.fetch_history()

    def clear_message_history(self):
        """
        Clears the message history from the backing database.
        """
        self._chat_history_backend.clear_history()

    def chat(self, prompt: str) -> List[Dict[str, str]]:
        """
        Chat with the backing LLM using the provided prompt. The agent will
        return the chat history after appending the user-provided prompt and
        the response from the LLM.

        Args:
            prompt (str): User-provided prompt.

        Returns:
            List[Dict[str, str]]: Message history where each entry in the list
                is a message with keys 'role' and 'content' representing the
                complete message history between the user and the LLM.
        """
        if prompt == "":
            return self._chat_history_backend.fetch_history()
        message_history = self._chat_history_backend.fetch_history()
        self._chat_history_backend.append_chat("user", prompt)
        response = self._llm_backend.chat(prompt=prompt,
                                          prev_messages=message_history)
        message_history = message_history + [{
            "role": "user",
            "content": prompt
        }, response]
        self._chat_history_backend.append_chat(response['role'],
                                               response['content'])
        return message_history
