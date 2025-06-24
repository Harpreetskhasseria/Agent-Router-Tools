import pdfkit
from pathlib import Path
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from typing import Dict

# Output directory
OUTPUT_DIR = Path("regulatory_outputs/site_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class FormatterInput(BaseModel):
    url: str = Field(..., description="The URL of the page")
    cleaned_file: str = Field(..., description="The path to the cleaned HTML file")


class FormatterTool(BaseTool):
    name: str = "formatter_tool"
    description: str = "Converts a cleaned HTML file into a formatted PDF using wkhtmltopdf"
    args_schema: type = FormatterInput

    def _run(self, url: str, cleaned_file: str) -> Dict:
        domain = urlparse(url).netloc.replace('.', '_')
        pdf_output_path = OUTPUT_DIR / f"{domain}_formatted.pdf"

        wkhtmltopdf_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        if not Path(wkhtmltopdf_path).exists():
            raise FileNotFoundError(f"wkhtmltopdf not found at: {wkhtmltopdf_path}")

        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        options = {
            'encoding': 'UTF-8',
            'enable-local-file-access': ''
        }

        try:
            pdfkit.from_file(cleaned_file, str(pdf_output_path), configuration=config, options=options)
            print(f"✅ PDF created: {pdf_output_path}")
        except Exception as e:
            print(f"❌ PDF conversion failed for {cleaned_file}: {e}")
            raise RuntimeError(f"PDF conversion failed: {e}")

        return {
            "url": url,
            "cleaned_file": cleaned_file,
            "pdf_file": str(pdf_output_path)
        }

formatter_tool = FormatterTool()

