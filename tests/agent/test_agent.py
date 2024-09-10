from google.generativeai.types import generation_types
import unittest
from unittest.mock import patch
import sqlite3
from mapchat.agent.agent import Agent
from tests.backends.helpers import (set_up_chat_history_backend_table,
                                    set_up_location_history_backend_table,
                                    tear_down_chat_history_backend_table,
                                    tear_down_location_history_backend_table)
from typing import Any, Dict, List


class AgentTestCase(unittest.TestCase):

    class DummyLLMBackend:

        def __init__(self):
            pass

        class DummyChat:

            class DummyResponse:

                def __init__(self, text: str):
                    self.text = text
                    self.parts = []

            def __init__(self):
                self.counter = 0

            def send_message(self, messages: List[Dict[str, str]]):
                self.counter += 1
                return self.DummyResponse("Response number %d" % self.counter)

        def start_chat(self, history: List[Dict[str, List[str]]]):
            return self.DummyChat()

    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        set_up_chat_history_backend_table(self.db)
        set_up_location_history_backend_table(self.db)

    def tearDown(self):
        tear_down_chat_history_backend_table(self.db)
        tear_down_location_history_backend_table(self.db)
        self.db.close()

    def test_message_history_empty(self):
        agent = Agent(self.db)
        agent._model = AgentTestCase.DummyLLMBackend()
        history = agent.message_history()
        self.assertEqual(len(history), 0)

    def test_chat_empty_prompt(self):
        agent = Agent(self.db)
        agent._model = AgentTestCase.DummyLLMBackend()
        prompt = ""
        response = agent.chat(prompt)
        self.assertEqual(len(response), 0)

    def test_chat_non_empty_prompt(self):
        agent = Agent(self.db)
        agent._model = AgentTestCase.DummyLLMBackend()
        prompt = "Hello, how are you?"
        response = agent.chat(prompt)
        self.assertEqual(len(response), 2)
        self.assertEqual(response[0]['role'], "user")
        self.assertEqual(response[0]['parts'], "Hello, how are you?")
        self.assertEqual(response[1]['role'], "model")
        self.assertEqual(response[1]['parts'], "Response number 1")

    def test_clear_message_history(self):
        agent = Agent(self.db)
        agent._model = AgentTestCase.DummyLLMBackend()
        agent.chat("Hello")
        agent.chat("How are you?")
        agent.clear_message_history()
        history = agent.message_history()
        self.assertEqual(len(history), 0)


if __name__ == '__main__':
    unittest.main()
