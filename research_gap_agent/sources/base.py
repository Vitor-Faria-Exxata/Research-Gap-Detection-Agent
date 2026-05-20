"""Common interface for all paper sources."""

from abc import ABC, abstractmethod

from research_gap_agent.schemas import Paper


class PaperSource(ABC):

    name: str

    @abstractmethod
    def search(self, query: str, limit: int) -> list[Paper]:
        """Return up to `limit` open-access papers matching `query`."""
