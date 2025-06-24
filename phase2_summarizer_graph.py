from pathlib import Path
import pandas as pd
import openpyxl
import re
import os

# === Import Tools and Agent ===
from tools.scraper_tool import scraper_tool
from tools.cleaner_tool import cleaner_tool
from tools.html_extractor_tool import html_extractor_tool
from agents.summarizer_agent import SummarizerAgent  # Updated path

# === Setup ===
INPUT_FOLDER = Path(r"C:/Users/hp/Documents/Agent Router Tools/regulatory_outputs/site_outputs")
INPUT_FILE = [f for f in INPUT_FOLDER.glob("*.xlsx") if "phase2_output" not in f.name][-1]
OUTPUT_FILE = INPUT_FOLDER / INPUT_FILE.with_stem(INPUT_FILE.stem + "_phase2_output").name

# === Step 1: Load Excel with openpyxl to extract hyperlink formulas ===
wb = openpyxl.load_workbook(INPUT_FILE)
sheet = wb.active

# Extract real hyperlinks from column G (Excel column "G" = index 6)
extracted_urls = []
for row in sheet.iter_rows(min_row=2, min_col=7, max_col=7):
    cell = row[0]
    formula = cell.value
    if isinstance(formula, str):
        match = re.search(r'HYPERLINK\("([^"]+)"', formula)
        if match:
            extracted_urls.append(match.group(1))
        else:
            extracted_urls.append(None)
    else:
        extracted_urls.append(None)

# === Step 2: Load DataFrame and apply URLs ===
df = pd.read_excel(INPUT_FILE)
df["action"] = df["action"].astype(str).fillna("")
df["Link"] = extracted_urls  # Replace with actual links

# === Agent ===
summarizer = SummarizerAgent()

# === Step 3: Execute Pipeline ===
results = []
for idx, row in df.iterrows():
    action = row["action"].strip()
    url = row.get("Link", "")

    if not action or action.lower() in ["skip", "nan"]:
        results.append(None)
        continue

    try:
        # Step 1: Scrape
        scrape_result = scraper_tool.run(url=url)
        cleaned_result = cleaner_tool.run(url=url, scraped_html=scrape_result["scraped_html"])
        extracted_result = html_extractor_tool.run(url=url, cleaned_file=cleaned_result["cleaned_file"])

        # Step 2: Summarize or Custom Prompt
        if action.lower() == "summarize":
            summary_output = summarizer.run({
                "extracted_text": extracted_result["extracted_text"],
                "url": url
            })
            results.append(summary_output["summary"])
        elif action.lower().startswith("custom:"):
            prompt = action[7:].strip()
            summarizer.goal = prompt
            summary_output = summarizer.run({
                "extracted_text": extracted_result["extracted_text"],
                "url": url
            })
            results.append(summary_output["summary"])
        else:
            results.append("❌ Unrecognized action")

    except Exception as e:
        results.append(f"❌ Error: {str(e)}")

# === Step 4: Save ===
df["phase2_output"] = results
df.to_excel(OUTPUT_FILE, index=False)
print(f"✅ Phase 2 output saved to: {OUTPUT_FILE}")
