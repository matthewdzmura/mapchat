from mapchat.backends.ollama_backend import ollama_chat


class Agent:
    """ Dummy Agent class. """

    def __init__(self):
        pass

    def chat(self, message_history, prompt):
        return ollama_chat(prompt, message_history)
