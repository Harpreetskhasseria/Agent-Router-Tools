from crewai import Agent
from pydantic import BaseModel
from pathlib import Path
from urllib.parse import urlparse
import os
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

# Load .env
load_dotenv("C:/Users/hp/Documents/Agent Router Tools/.env")

# Output directory
OUTPUT_DIR = Path("regulatory_outputs/site_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Input/Output Schemas
class SummarizerInput(BaseModel):
    text: str | None = None
    source_url: str | None = None
    extracted_text: str | None = None
    url: str | None = None

class SummarizerOutput(BaseModel):
    source_url: str
    summary: str
    summary_file: str

class SummarizerAgent(Agent):
    def __init__(self):
        super().__init__(
            name="SummarizerAgent",
            role="Regulatory Summarizer",
            goal="Summarize updates with focus on impact to large banks like Wells Fargo.",
            backstory="You are a regulatory analyst summarizing updates for compliance professionals at global banks."
        )

    def run(self, input_data: dict) -> dict:
        # Accept flexible inputs
        if "text" in input_data and "source_url" in input_data:
            text = input_data["text"]
            source_url = input_data["source_url"]
        elif "extracted_text" in input_data and "url" in input_data:
            text = input_data["extracted_text"]
            source_url = input_data["url"]
        else:
            raise ValueError("❌ Input must include ('text' + 'source_url') or ('extracted_text' + 'url')")

        # Prompt
        prompt = f"""
You are a regulatory analyst focused on large global financial institutions such as Wells Fargo.

Summarize the following content from a regulatory update. Your summary should highlight:

1. Key regulatory developments or announcements.
2. Implications or potential impact on large banks like Wells Fargo or their global peers.
3. Any new obligations, risk areas, or disclosures mentioned.

Respond in 2–4 sentences. Be precise and compliance-focused.

Content:
{text}
"""

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        summary = response.choices[0].message.content.strip()

        domain = urlparse(source_url).netloc.replace(".", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = OUTPUT_DIR / f"{domain}_summary_{timestamp}.txt"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)

        print(f"✅ Saved summary to: {summary_file}")

        return {
            "source_url": source_url,
            "summary": summary,
            "summary_file": str(summary_file)
        }
