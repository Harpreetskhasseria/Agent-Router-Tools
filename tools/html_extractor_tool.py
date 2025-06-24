from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from urllib.parse import urlparse, urljoin
from pathlib import Path
from typing import List, Dict
from crewai.tools import BaseTool

# ✅ Output directory
OUTPUT_DIR = Path(r"C:\Users\hp\Documents\Agent Router Tools\regulatory_outputs\site_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ✅ Input schema
class HTMLExtractorInput(BaseModel):
    url: str = Field(..., description="The URL of the page")
    cleaned_file: str = Field(..., description="The path to the cleaned HTML file")

# ✅ Tool class
class HTMLExtractorTool(BaseTool):
    name: str = "html_extractor_tool"
    description: str = "Extracts visible text and links from cleaned HTML content"
    args_schema: type = HTMLExtractorInput

    def _run(self, url: str, cleaned_file: str) -> Dict:
        def extract_visible_text_and_links(html_path: str, base_url: str = "") -> tuple[str, List[str]]:
            with open(html_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")

            for tag in soup(["script", "style", "noscript", "footer", "header", "nav", "aside"]):
                tag.decompose()

            result = []

            def traverse(node):
                if isinstance(node, NavigableString):
                    text = node.strip()
                    if text:
                        result.append(text)
                elif isinstance(node, Tag):
                    if node.name == "a" and node.get("href"):
                        text = node.get_text(strip=True)
                        href = urljoin(base_url, node["href"])
                        if text:
                            result.append(f"{text} ({href})")
                    else:
                        for child in node.children:
                            traverse(child)

            traverse(soup.body or soup)
            visible_text = " ".join(result)
            links = [part.split(" (")[-1].rstrip(")") for part in result if " (" in part]
            return visible_text, list(set(links))

        print(f"🔍 Extracting from: {cleaned_file}")
        visible_text, links = extract_visible_text_and_links(cleaned_file, url)

        domain = urlparse(url).netloc.replace(".", "_")
        output_path = OUTPUT_DIR / f"{domain}_extracted.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(visible_text)

        print(f"✅ Saved extracted content to: {output_path}")

        return {
            "url": url,
            "extracted_text": visible_text,
            "extracted_links": links,
            "extracted_file": str(output_path)
        }

html_extractor_tool = HTMLExtractorTool()
