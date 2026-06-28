from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable

class BaseAgent(ABC):
    """
    Tüm alt ajanların (Sub-Agents) miras alacağı Abstract Base Class.
    Modülerlik ve genişletilebilirlik (Scalability) için interface'i belirler.
    """
    def __init__(self, name: str, model_client: Any = None):
        self.name = name
        self.model_client = model_client
        self.tools: Dict[str, Callable] = {}

    def register_tool(self, name: str, func: Callable):
        """Ajana dinamik olarak yeni bir tool (fonksiyon) tanımlar."""
        self.tools[name] = func

    @abstractmethod
    async def run(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Ajanın ana çalışma döngüsü. Her alt ajan bu metodu ezmek zorundadır.
        """
        pass

    @abstractmethod
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        LLM'e (Tool-Calling için) beslenecek fonksiyon şemalarını (JSON Schema) döner.
        """
        pass