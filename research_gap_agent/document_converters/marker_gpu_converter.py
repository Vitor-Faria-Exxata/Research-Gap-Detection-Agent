from .document_converter import DocumentConverter
from research_gap_agent.document_converters import ensure_local_file

class MarkerGPUConverter(DocumentConverter):
    def __init__(self):
        try:
            from marker.convert import convert_single_pdf
            from marker.models import load_all_models
            self.convert_single_pdf = convert_single_pdf
            self.models = load_all_models()
        
        except ImportError:
            raise ImportError(
                "Marker is not installed. "
                "Please install it using: pip install marker-pdf"
            )
        
    def convert(self, source: str) -> str:
        with ensure_local_file(source) as local_path:
            full_text, _, _ = self.convert_single_pdf(local_path, self.models)
            return full_text

    def convert_batch(self, sources: list[str]) -> list[str]:
        results = []
        for source in sources:
            try:
                results.append(self.convert(source))
            except Exception as e:
                results.append(f"Error processing {source}: {str(e)}")
        return results