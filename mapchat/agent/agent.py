import datetime
import os

import google.generativeai as genai
from google.generativeai.types import content_types
from google.generativeai.protos import Content, Part

import logging

from mapchat.backends.chat_history_backend import ChatHistoryBackend
from mapchat.backends.location_history_backend import LocationHistoryBackend

import sqlite3
from typing import Dict, List, Union

logger = logging.getLogger(__name__)


class Agent:
    """ Dummy Agent class. """

    def __init__(self, db: sqlite3.Connection):
        self._location_history_backend = LocationHistoryBackend(db)
        self._chat_history_backend = ChatHistoryBackend(db)
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        # Create the model
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        safety_settings = {
            'HATE': 'BLOCK_NONE',
            'HARASSMENT': 'BLOCK_NONE',
            'SEXUAL': 'BLOCK_NONE',
            'DANGEROUS': 'BLOCK_NONE'
        }

        self._model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            tools=[self._location_history_backend.gemini_tool_proto()],
            # safety_settings = Adjust safety settings
            # See https://ai.google.dev/gemini-api/docs/safety-settings
            safety_settings=safety_settings)

    def message_history(self) -> List[Dict[str, str]]:
        """
        Fetches the chat history from the backing database using the
        connection.

        Returns:
            List[Dict[str, str]]: Message history where each entry in the
                returned list is a message with keys 'role' and 'parts'.
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
            List[Dict[str, str]]: Message history where each
                entry in the list is a message with keys 'role' and 'parts'
                representing the complete message history between the user and
                the LLM.
        """
        # Nothing to be done if prompt is empty.
        if prompt == "":
            return self._chat_history_backend.fetch_history()

        # Grab the message history and append the new chat to the database.
        message_history = self._chat_history_backend.fetch_history()
        history = [{
            'role': message['role'],
            'parts': [message['parts']]
        } for message in message_history]
        logger.debug("Starting chat with history: %s", str(history))
        chat = self._model.start_chat(history=history)
        logger.debug("Sending initial message with prompt: %s", prompt)
        response = chat.send_message(prompt)
        logger.debug("Received response: %s", str(response))

        tool_responses = {}
        for part in response.parts:
            if fn := part.function_call:
                # Create the args, escaping string values as necessary.
                args = [(key, f"\"\"\"{val.replace('\"', '\'')}\"\"\""
                         if isinstance(val, str) else val)
                        for key, val in fn.args.items()]
                args = ", ".join(f"{key}={val}" for key, val in args)

                # Gemini didn't return any function name when queried with
                # self._location_history_backend.execute_query, so create a
                # dummy function to execute for now.
                def execute_query(query: str):
                    return self._location_history_backend.execute_query(query)

                logger.debug("Executing function call: %s(%s)", fn.name, args)

                # Perform function call, get response.
                local_vars = locals()
                fn_response = ""
                exec(f"fn_response = {fn.name}({args})", globals(), local_vars)
                fn_response = local_vars.get('fn_response')
                logger.debug("Function call response: %s", str(fn_response))
                tool_responses[fn.name] = str(fn_response)

        # Now that we've executed all the tools and gotten responses, send
        # another chat to Gemini to get the final response.
        response_parts = [
            genai.protos.Part(function_response=genai.protos.FunctionResponse(
                name=fn, response={"result": val}))
            for fn, val in tool_responses.items()
        ]
        if (len(response_parts) > 0):
            logger.debug("Sending tool use results: %s", str(response_parts))
            response = chat.send_message(response_parts)
            logger.debug("Tool use followup response: %s", str(response))
        else:
            logger.debug("No tool responses, passing on text to user.")

        message_history += [{
            "role": "user",
            "parts": prompt
        }, {
            "role": "model",
            "parts": response.text
        }]

        # Append the response to the message history and the chat database.
        self._chat_history_backend.append_chat("user", prompt)
        self._chat_history_backend.append_chat(message_history[-1]['role'],
                                               message_history[-1]['parts'])

        # Return the complete chat history with the new additions.
        logger.debug("Returning final message history: %s",
                     str(message_history))
        return message_history
