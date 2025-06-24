from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from typing import Dict

# Output folder
OUTPUT_DIR = Path("regulatory_outputs/site_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Tags to remove from HTML
TAGS_TO_REMOVE = ["script", "style", "noscript", "footer", "header", "nav", "aside"]

class CleanerInput(BaseModel):
    url: str = Field(..., description="The original URL of the page")
    scraped_html: str = Field(..., description="The raw HTML content to be cleaned")

class CleanerTool(BaseTool):
    name: str = "cleaner_tool"
    description: str = "Cleans raw HTML by removing unnecessary tags and outputs cleaned HTML and saved file path"
    args_schema: type = CleanerInput

    def _run(self, url: str, scraped_html: str) -> Dict:
        def clean_html_content(raw_html: str) -> str:
            soup = BeautifulSoup(raw_html, "html.parser")
            for tag in TAGS_TO_REMOVE:
                for element in soup.find_all(tag):
                    element.decompose()
            for tag in soup.find_all():
                if not tag.get_text(strip=True) and tag.name not in ["br", "hr"]:
                    tag.decompose()
            return soup.prettify()

        cleaned_html = clean_html_content(scraped_html)

        domain = urlparse(url).netloc.replace('.', '_')
        output_path = OUTPUT_DIR / f"{domain}_cleaned.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned_html)

        print(f"✅ Cleaned HTML saved to: {output_path}")

        return {
            "url": url,
            "cleaned_html": cleaned_html,
            "cleaned_file": str(output_path)
        }

cleaner_tool = CleanerTool()
