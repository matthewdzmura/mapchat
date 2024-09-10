import sqlite3
from typing import Dict, List


class ChatHistoryBackend:
    """
    Simple backend for storing chat history in a sqlite3 database.
    
    Args:
        db (sqlite3.Connection): sqlite3 connection to a backing database
            where the chat history is stored.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        """_summary_

        Args:
            db (sqlite3.Connection): _description_
        """
        self._db = db

    def fetch_history(self) -> List[Dict[str, str]]:
        """
        Fetches the chat history from the backing database using the connection
        supplied in self._db. Messages are returned in the order they were
        added to the database.

        Returns:
            List[Dict[str,str]]: List of messages where each message is a
                Dict[str,str] with key/value pairs for role and content of
                each message.
        """
        cur = self._db.cursor()
        result = cur.execute(
            "SELECT role, parts FROM chat ORDER BY ID").fetchall()
        message_history = [{"role": row[0], "parts": row[1]} for row in result]
        return message_history

    def append_chat(self, role: str, parts: str) -> None:
        """
        Appends the provided chat to the end of the chat history.
        
        Args:
            role(str): Role for the message. For Llama 3.1 can be 'user',
                'assistant', 'system', or 'ipython'
            parts(str): Content of the message itself.
        """
        cur = self._db.cursor()
        cur.execute("""INSERT INTO chat (role, parts) VALUES(?, ?)""",
                    (role, parts))
        self._db.commit()

    def clear_history(self) -> None:
        """
        Clears all existing chat history.
        """
        cur = self._db.cursor()
        cur.execute("""DELETE FROM chat;""")
        self._db.commit()
