from abc import ABC, abstractmethod

class DocumentConverter(ABC):
    """Base interface for converting documents to Markdown."""
    
    @abstractmethod
    def convert(self, source: str) -> str:
        """Converts a single document."""
        pass

    @abstractmethod
    def convert_batch(self, sources: list[str]) -> list[str]:
        """
        Converts a batch of documents using the optimal concurrency 
        strategy for the specific provider.
        """
        pass