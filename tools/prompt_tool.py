from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from typing import Dict
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env file from specified path
load_dotenv("C:/Users/hp/Documents/Agent Router Tools/.env")

# Initialize OpenAI client with API key from .env
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Output directory
OUTPUT_DIR = Path("regulatory_outputs/site_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class PromptToolInput(BaseModel):
    url: str = Field(..., description="The original URL of the page")
    full_text: str = Field(..., description="The full text extracted from the URL")
    custom_prompt: str = Field(..., description="The user-defined prompt to apply to the text")

class PromptTool(BaseTool):
    name: str = "prompt_tool"
    description: str = "Applies a user-defined prompt to the given text using an LLM and returns the response"
    args_schema: type = PromptToolInput

    def _run(self, url: str, full_text: str, custom_prompt: str) -> Dict:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain = urlparse(url).netloc.replace('.', '_')
        output_file = OUTPUT_DIR / f"{domain}_prompt_output_{timestamp}.txt"

        try:
            # Combine prompt and full text
            full_input = f"{custom_prompt.strip()}\n\n---\n\n{full_text.strip()}"

            # Call OpenAI
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": full_input}
                ],
                temperature=0.3
            )

            llm_response = response.choices[0].message.content.strip()

            # Save both prompt and response
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("### Prompt:\n")
                f.write(custom_prompt.strip())
                f.write("\n\n### Response:\n")
                f.write(llm_response)

            print(f"✅ Prompt output saved to: {output_file}")

            return {
                "url": url,
                "llm_response": llm_response,
                "output_file": str(output_file)
            }

        except Exception as e:
            return {
                "url": url,
                "llm_response": f"❌ Error: {str(e)}",
                "output_file": None
            }

prompt_tool = PromptTool()
