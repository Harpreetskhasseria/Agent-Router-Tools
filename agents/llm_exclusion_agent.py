import os
import json
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from urllib.parse import urlparse
from datetime import datetime
from pydantic import BaseModel
from crewai import Agent
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

# Load environment variables
load_dotenv("C:/Users/hp/Documents/Agent Router Tools/.env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Output directory
OUTPUT_DIR = Path("regulatory_outputs/site_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Input/output schema
class LLMExclusionInput(BaseModel):
    url: str
    extracted_file: str  # path to CSV file

class LLMExclusionOutput(BaseModel):
    url: str
    exclusion_file: str  # path to XLSX

class LLMExclusionAgent(Agent):
    def __init__(self):
        super().__init__(
            name="LLMExclusionAgent",
            role="LLM-based Compliance Exclusion Filter",
            goal="Decide whether each link and associated text should be included in compliance monitoring.",
            backstory="You support compliance by reviewing extracted web content using LLMs and filtering out irrelevant links."
        )
        self.prompt_template = """
You are a compliance filtering assistant for a U.S. bank.

Given the topic, supporting context, and regulator source, decide whether this content is relevant for compliance monitoring.

Respond in JSON format like this:
{{
  "recommendation": "Include" or "Exclude",
  "reason": "short explanation"
}}

Topic: {topic}
Context: {context}
Regulator: {regulator}
"""

    def _review_llm(self, topic: str, context: str, regulator: str):
        topic = str(topic).strip() if pd.notnull(topic) else ""
        context = str(context).strip() if pd.notnull(context) else ""
        regulator = str(regulator).strip() if pd.notnull(regulator) else ""

        prompt = self.prompt_template.format(
            topic=topic[:300],
            context=context[:1000],
            regulator=regulator
        )
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a compliance content classifier."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            content = response.choices[0].message.content.strip()
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start == -1 or json_end == -1:
                raise ValueError("No JSON object found in LLM response")

            parsed = json.loads(content[json_start:json_end])
            if "recommendation" not in parsed or "reason" not in parsed:
                raise ValueError("Missing required keys in parsed LLM output")

            return parsed

        except Exception as e:
            print(f"⚠️ Failed to parse LLM output: {e}")
            return {
                "recommendation": "Exclude",
                "reason": f"⚠️ LLM error or invalid output: {str(e)}"
            }

    def run(self, input_data: dict) -> dict:
        if "extracted_file" not in input_data and "llm_output_file" in input_data:
            input_data["extracted_file"] = input_data.pop("llm_output_file")

        input_obj = LLMExclusionInput(**input_data)
        file_path = Path(input_obj.extracted_file)
        url = input_obj.url

        if not file_path.exists():
            raise FileNotFoundError(f"❌ Extracted file not found at: {file_path}")

        # ✅ Read CSV input
        df = pd.read_csv(file_path)

        required_cols = {"topic", "additional_context", "regulator", "link"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"❌ Required columns missing: {required_cols - set(df.columns)}")

        df["Recommendation"] = ""
        df["Reason"] = ""

        print(f"🔍 Reviewing {len(df)} updates for exclusion...")

        for i, row in df.iterrows():
            topic = row.get("topic", "")
            context = row.get("additional_context", "")
            regulator = row.get("regulator", "")
            result = self._review_llm(topic, context, regulator)
            df.at[i, "Recommendation"] = result.get("recommendation", "Exclude")
            df.at[i, "Reason"] = result.get("reason", "No reason provided")

        # ✅ Convert 'link' to Excel-formatted clickable hyperlinks
        df["Link"] = df["link"].apply(
            lambda x: f'=HYPERLINK("{x}", "Open Link")' if pd.notna(x) and str(x).startswith("http") else ""
        )
        df.drop(columns=["link"], inplace=True)

        # ✅ Add editable action column with dropdown
        df["action"] = ""

        domain = urlparse(url).netloc.replace('.', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = OUTPUT_DIR / f"{domain}_llm_exclusion_checked_{timestamp}.xlsx"

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Exclusion Results")
            workbook = writer.book
            sheet = writer.sheets["Exclusion Results"]

            # Find column index of 'action'
            action_col_idx = df.columns.get_loc("action") + 1
            action_col_letter = get_column_letter(action_col_idx)

            # ✅ Working dropdown logic
            dv = DataValidation(
                type="list",
                formula1='"summarize,custom prompt,no action"',
                allow_blank=True,
                showDropDown=False  # must be False to show the dropdown arrow
            )
            dv.error = "Invalid input. Choose from summarize, custom prompt, or no action."
            dv.errorTitle = "Invalid Action"

            # Apply to rows 2–101 (100 rows)
            dv.add(f"{action_col_letter}2:{action_col_letter}101")
            sheet.add_data_validation(dv)

        print(f"✅ Exclusion results saved to: {output_path}")

        return LLMExclusionOutput(
            url=url,
            exclusion_file=str(output_path)
        ).dict()
