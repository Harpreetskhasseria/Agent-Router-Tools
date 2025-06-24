import feedparser
from pydantic import BaseModel, Field
from typing import List, Dict
from urllib.parse import urlparse
from pathlib import Path
from crewai.tools import BaseTool

# ✅ Absolute path to save RSS outputs
OUTPUT_DIR = Path(r"C:\Users\hp\Documents\Agent Store 1 - Copy\regulatory_outputs\site_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class RSSFetcherInput(BaseModel):
    url: str = Field(..., description="URL of the RSS or Atom feed")


class RSSFetcherTool(BaseTool):
    name: str = "rss_fetcher_tool"
    description: str = "Fetches and parses RSS/Atom feed content for LLM extraction"
    args_schema: type = RSSFetcherInput

    def _run(self, url: str) -> Dict:
        parsed = feedparser.parse(url)
        entries = parsed.entries[:25]

        result_lines = []
        links = []

        for entry in entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
            link = entry.get("link", "")
            date = entry.get("published", "") or entry.get("updated", "")
            result_lines.append(f"Title: {title}\nDate: {date}\nSummary: {summary}\nLink: {link}\n---\n")
            if link:
                links.append(link)

        visible_text = "\n".join(result_lines)
        unique_links = list(set(links))

        domain = urlparse(url).netloc.replace('.', '_')
        output_path = OUTPUT_DIR / f"{domain}_rss_extracted.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(visible_text)

        print(f"✅ RSS content saved to: {output_path}")

        return {
            "url": url,
            "extracted_text": visible_text,
            "extracted_links": unique_links,
            "extracted_file": str(output_path)
        }

rss_fetcher_tool = RSSFetcherTool()
