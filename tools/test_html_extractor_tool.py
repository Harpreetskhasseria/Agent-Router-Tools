# test_html_extractor_tool.py

import sys
import os

# Ensure parent folder is on path so tools can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.html_extractor_tool import html_extractor_tool

# ✅ Update with a real cleaned HTML file path you already have
test_input = {
    "url": "https://www.bis.org/press/pressrel.htm",
    "cleaned_file": "regulatory_outputs/site_outputs/www_bis_org_scraped.html"
}

# Run the tool
result = html_extractor_tool.run(**test_input)

# Show results
print("\n✅ Tool Output:")
print(result)
