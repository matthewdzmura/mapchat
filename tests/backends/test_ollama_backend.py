import unittest
from unittest.mock import patch, MagicMock
import json
from mapchat.backends.ollama_backend import ollama_chat


class TestOllamaChat(unittest.TestCase):

    @patch('mapchat.backends.ollama_backend.requests.post')
    def test_ollama_chat_valid_response(self, mock_post):
        # Mock response
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            json.dumps({
                "message": {
                    "content": "Hello"
                },
                "done": False
            }).encode('utf-8'),
            json.dumps({
                "done": True
            }).encode('utf-8')
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        prompt = "Hi"
        prev_messages = [{"role": "user", "content": "Hello"}]
        result = ollama_chat(prompt, prev_messages)

        self.assertEqual(result, {"role": "assistant", "content": "Hello"})

    @patch('mapchat.backends.ollama_backend.requests.post')
    def test_ollama_chat_error_response(self, mock_post):
        # Mock response with error
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            json.dumps({
                "error": "Something went wrong"
            }).encode('utf-8')
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        prompt = "Hi"
        prev_messages = [{"role": "user", "content": "Hello"}]

        with self.assertRaises(Exception) as context:
            ollama_chat(prompt, prev_messages)

        self.assertTrue("Something went wrong" in str(context.exception))


if __name__ == '__main__':
    unittest.main()
