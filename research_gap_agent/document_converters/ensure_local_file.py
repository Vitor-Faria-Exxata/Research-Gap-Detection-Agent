import os
import tempfile
import contextlib

@contextlib.contextmanager
def ensure_local_file(source: str):
    """
    If the source is a URL, downloads it to a temporary file, yields the path, 
    and cleans it up afterward. If it's already a local path, just yields it.
    """
    if source.startswith("http://") or source.startswith("https://"):
        import requests 
        
        response = requests.get(source, stream=True)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_path = temp_file.name
            
        try:
            yield temp_path
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    else:
        yield source