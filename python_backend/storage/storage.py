from abc import ABC, abstractmethod

class StorageProvider(ABC):
    @abstractmethod
    def upload(self, context, file, filename: str, content_type: str) -> str:
        pass

    @abstractmethod
    def delete(self, context, file_url: str):
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass
