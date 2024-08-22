from mapchat.backends.chat_history_backend import ChatHistoryBackend

import sqlite3
import unittest


class ChatHistoryBackendTest(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        cursor = self.conn.cursor()
        cursor.executescript("""
            DROP TABLE IF EXISTS chat;

            CREATE TABLE chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_chat_history_backend(self):
        backend = ChatHistoryBackend(self.conn)

        backend.append_chat("user", "message1")
        backend.append_chat("assistant", "message2")
        backend.append_chat("user", "message3")
        self.assertEqual(backend.fetch_history(), [{
            "role": "user",
            "content": "message1"
        }, {
            "role": "assistant",
            "content": "message2"
        }, {
            "role": "user",
            "content": "message3"
        }])

        backend.append_chat("assistant", "message4")
        self.assertEqual(backend.fetch_history(), [{
            "role": "user",
            "content": "message1"
        }, {
            "role": "assistant",
            "content": "message2"
        }, {
            "role": "user",
            "content": "message3"
        }, {
            "role": "assistant",
            "content": "message4"
        }])

        backend.clear_history()
        self.assertEqual(backend.fetch_history(), [])
