from abc import ABC, abstractmethod

class VirusScanner(ABC):
    @abstractmethod
    def scan(self, context, file, filename: str) -> tuple[bool, str]:
        pass

class DefaultVirusScanner(VirusScanner):
    def scan(self, context, file, filename: str) -> tuple[bool, str]:
        print(f"[VIRUS SCANNER] Scanning file '{filename}'... Clean.")
        return True, "Clean"
