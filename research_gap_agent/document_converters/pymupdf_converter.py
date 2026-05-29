from .document_converter import DocumentConverter
import concurrent
from .ensure_local_file import ensure_local_file

def _pymupdf_worker(source: str) -> str:
    """Standalone function that can be safely pickled and sent to other CPU cores."""
    
    import pymupdf4llm 
    
    with ensure_local_file(source) as local_path:
        return pymupdf4llm.to_markdown(local_path)

class PyMuPDFConverter(DocumentConverter):
    def __init__(self):
        try:
            import pymupdf4llm
        except ImportError:
            raise ImportError(
                "PyMuPDF4LLM is not installed. "
                "Please install it using: pip install pymupdf4llm"
            )

    def convert(self, source: str) -> str:
        return _pymupdf_worker(source)
            
    def convert_batch(self, sources: list[str]) -> list[str]:
        with concurrent.futures.ProcessPoolExecutor() as executor:
            return list(executor.map(_pymupdf_worker, sources))