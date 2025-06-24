import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.llm_extractor_tool import llm_extractor_tool


# Replace these with actual valid paths
test_input = {
    "url": "https://www.bis.org/press/pressrel.htm",
    "extracted_text": """
        The Bank for International Settlements released a new report on central bank digital currencies (CBDCs) on June 15, 2025.
        The report emphasizes the importance of cross-border cooperation and technical standards.
        More updates will follow next month.
    """
}

# Run the tool
result = llm_extractor_tool.run(**test_input)

print("✅ Tool output:")
print(result)
 	 	