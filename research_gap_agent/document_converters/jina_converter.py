from .document_converter import DocumentConverter
import concurrent

class JinaConverter(DocumentConverter):
    def __init__(self, api_key: str = None):
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.base_url = "https://r.jina.ai/"

    def convert(self, source: str) -> str:
        # ... single HTTP request logic ...
        pass

    def convert_batch(self, sources: list[str]) -> list[str]:
        # I/O bound: Blast it with a ThreadPool
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Maintains the order of the input list
            return list(executor.map(self.convert, sources))