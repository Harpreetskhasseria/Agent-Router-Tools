from pydantic import BaseModel, Field
from typing import Dict
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from crewai.tools import BaseTool

# Create output directory
OUTPUT_DIR = Path("regulatory_outputs/site_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


class ScraperInput(BaseModel):
    url: str = Field(..., description="The URL of the website to scrape")


class ScraperTool(BaseTool):
    name: str = "scraper_tool"
    description: str = "Scrapes raw HTML content from the provided URL and saves it as a file"
    args_schema: type = ScraperInput

    def _run(self, url: str) -> Dict:
        async def fetch_html(target_url: str) -> str:
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.goto(target_url, timeout=60000)
                    await page.wait_for_timeout(5000)

                    await page.evaluate(
                        """(base) => {
                            document.querySelectorAll('a[href]').forEach(a => {
                                const href = a.getAttribute('href');
                                if (href && !href.startsWith('http')) {
                                    a.setAttribute('href', new URL(href, base).href);
                                }
                            });
                        }""",
                        target_url
                    )

                    html = await page.content()
                    await browser.close()
                    return html

            except Exception as e:
                return (
                    f"<html><body><h1>Error scraping {target_url}</h1><p>{str(e)}</p></body></html>"
                )

        html_content = asyncio.run(fetch_html(url))

        domain = urlparse(url).netloc.replace('.', '_')
        output_path = OUTPUT_DIR / f"{domain}_scraped.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"✅ Scraped content saved to {output_path}")

        return {
            "url": url,
            "html": html_content, 
            "scraped_html": html_content,
            "scraped_file": str(output_path)
        }

scraper_tool = ScraperTool()

