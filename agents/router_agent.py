# router_agent.py

import os
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv
from openai import OpenAI
from crewai import Agent

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class RouterAgent(Agent):
    def __init__(self):
        super().__init__(
            name="RouterAgent",
            role="Routing Decision Maker",
            goal="Decide whether the URL is an RSS feed or a webpage.",
            backstory="You intelligently decide how to process a URL using heuristics and LLM if needed."
        )

    def _looks_like_rss(self, url: str) -> bool:
        # Basic heuristic check
        return url.endswith(".xml") or "rss" in url.lower()

    def _fetch_preview(self, url: str) -> str:
        try:
            resp = requests.get(url, timeout=5)
            text = resp.text[:2000]  # Just a preview
            return text
        except Exception as e:
            print(f"⚠️ Error fetching URL: {e}")
            return ""

    def _llm_classify(self, url: str, text_preview: str) -> str:
        prompt = f"""
You are a smart URL classifier.

Given the following preview of a URL's content, decide if it is an RSS feed or a regular webpage.

Output ONLY one word: "rss" or "web". No explanation.

URL: {url}

Content Preview:
{text_preview}
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Classify the type of URL."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=5
            )
            result = response.choices[0].message.content.strip().lower()
            return "rss" if "rss" in result else "web"
        except Exception as e:
            print(f"⚠️ LLM classification failed: {e}")
            return "web"  # Default to web if LLM fails

    def run(self, input_data: dict) -> dict:
        url = input_data["url"]

        # 1. Heuristic check
        if self._looks_like_rss(url):
            return {"route": "rss"}

        # 2. Fetch preview
        preview = self._fetch_preview(url)

        # 3. Use LLM to classify
        route = self._llm_classify(url, preview)
        print(f"🔁 RouterAgent selected route: {route}")
        return {"route": route}
 	