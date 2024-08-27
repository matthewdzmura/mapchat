from typing import Dict, List, Protocol


class LLMBackendProtocol(Protocol):

    def chat(self, **kwargs) -> Dict[str, str]:
        ...
