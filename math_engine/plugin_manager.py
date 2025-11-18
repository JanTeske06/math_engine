from pathlib import Path
from abc import ABC, abstractmethod
from decimal import  Decimal

class BasePlugin(ABC):

    @property
    @abstractmethod
    def min_args(self) -> int:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def execute(self, args: list) -> Decimal:
        pass

    def get_help(self) -> str:
        return "Keine Hilfe verfügbar."


def find_plugins():
    plugin_ordner = Path("./plugins")
    if not plugin_ordner.exists():
        print("Warnung: Kein 'plugins' Ordner gefunden!")
        return []

    print(f"Scanne Ordner: {plugin_ordner.absolute()}")
    for datei in plugin_ordner.glob("*.py"):
        if datei.name == "__init__.py":
            continue
        print(f"Plugin-Datei entdeckt: {datei.name}")


def load_plugin():
    print("x")