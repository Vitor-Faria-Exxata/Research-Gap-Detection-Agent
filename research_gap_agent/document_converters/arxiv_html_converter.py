from .document_converter import DocumentConverter
import concurrent

class ArxivHtmlFallbackConverter(DocumentConverter):
    def __init__(self):
        try:
            import requests
            from bs4 import BeautifulSoup
            import markdownify
            
            # Bind the modules to the class instance
            self.requests = requests
            self.BeautifulSoup = BeautifulSoup
            self.markdownify = markdownify
        except ImportError as e:
            raise ImportError(
                f"Missing dependency for ArxivHtmlFallbackConverter: {e}. "
                "Please install required packages: pip install requests beautifulsoup4 markdownify"
            )

    def convert(self, source: str) -> str:
        url = f"https://arxiv.org/html/{source}"
        
        response = self.requests.get(url)
        
        if response.status_code != 200:
            raise ValueError(f"HTML version not available for {source}")
            
        html_content = response.text
        
        if "ltx_ERROR" in html_content or "\\textbf{" in html_content:
            raise ValueError(f"Heavy conversion errors detected in HTML for {source}")
            
        soup = self.BeautifulSoup(html_content, "html.parser")
        article_body = soup.find('div', class_='ltx_page_content')# or soup.find("article") or soup.find("body")
        
        if not article_body:
            raise ValueError("Could not locate the main article body in the HTML.")
            
        markdown_text = self.markdownify.markdownify(
            str(article_body),
            heading_style="ATX",
            strip=['script', 'style']
        )
        
        return markdown_text.strip()

    def convert_batch(self, sources: list[str]) -> list[str]:
        """
        Fetches HTML versions concurrently.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            return list(executor.map(self._safe_convert, sources))