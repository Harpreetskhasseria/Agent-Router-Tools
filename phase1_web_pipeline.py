from langgraph.graph import StateGraph
from typing import TypedDict
import asyncio
import os
from urllib.parse import urlparse

# Import tools and agents
from tools.scraper_tool import ScraperTool
from tools.cleaner_tool import CleanerTool
from tools.html_extractor_tool import HTMLExtractorTool
from tools.llm_extractor_tool import LLMExtractorTool
from agents.llm_exclusion_agent import LLMExclusionAgent
from agents.router_agent import RouterAgent

# Initialize tools and agents
scraper_tool = ScraperTool()
cleaner_tool = CleanerTool()
html_extractor_tool = HTMLExtractorTool()
llm_extractor_tool = LLMExtractorTool()
exclusion_agent = LLMExclusionAgent()
router_agent = RouterAgent()

# Define shared state
class State(TypedDict):
    url: str
    route: str
    scraper_input: dict
    scraper_output: dict
    cleaner_input: dict
    cleaner_output: dict
    html_extractor_input: dict
    html_extractor_output: dict
    llm_extractor_input: dict
    llm_extractor_output: dict
    exclusion_input: dict
    exclusion_output: dict
    final_output: dict

# Node: Router
# Node: Router
def router_node(state: State) -> State:
    route = router_agent.run({"url": state["url"]})
    print(f"🧭 Routing URL via RouterAgent... ➤ {route}")
    return {"route": route["route"]}


# Node: Scraper
def scraper_node(state: State) -> State:
    input_dict = state.get("scraper_input", {"url": state["url"]})
    output = scraper_tool.run(**input_dict)
    return {
        "scraper_output": output,
        "cleaner_input": {
            "url": output["url"],
            "scraped_html": output["scraped_html"]
        }
    }

# Node: Cleaner
def cleaner_node(state: State) -> State:
    output = cleaner_tool.run(**state["cleaner_input"])
    return {
        "cleaner_output": output,
        "html_extractor_input": {
            "url": output["url"],
            "cleaned_file": output["cleaned_file"]
        }
    }

# Node: HTML Extractor
def html_extractor_node(state: State) -> State:
    output = html_extractor_tool.run(**state["html_extractor_input"])
    return {
        "html_extractor_output": output,
        "llm_extractor_input": {
            "url": output["url"],
            "extracted_file": output["extracted_file"]
        }
    }

# Node: LLM Extractor
def llm_extractor_node(state: State) -> State:
    output = llm_extractor_tool.run(**state["llm_extractor_input"])
    return {
        "llm_extractor_output": output,
        "exclusion_input": {
            "url": state["url"],
            "extracted_file": output["output_file"]
        }
    }

# ✅ Updated Node: Exclusion Agent with output file detection
def exclusion_node(state: State) -> State:
    print("Using Tool: llm_exclusion_agent")
    output = exclusion_agent.run(state["exclusion_input"])

    domain = urlparse(state["url"]).netloc.replace(".", "_")
    folder = "regulatory_outputs/site_outputs"
    latest_file = None

    try:
        files = sorted(
            [f for f in os.listdir(folder) if f.startswith(domain) and f.endswith(".xlsx")],
            key=lambda f: os.path.getmtime(os.path.join(folder, f)),
            reverse=True
        )
        if files:
            latest_file = os.path.join(folder, files[0])
    except Exception as e:
        print(f"⚠️ Could not detect output file: {e}")

    return {
        "final_output": {
            "output_file": latest_file if latest_file else "",
            "data": output
        }
    }

# Build the LangGraph
graph = StateGraph(State)

# Add nodes
graph.add_node("router", router_node)
graph.add_node("scraper", scraper_node)
graph.add_node("cleaner", cleaner_node)
graph.add_node("html_extractor", html_extractor_node)
graph.add_node("llm_extractor", llm_extractor_node)
graph.add_node("exclusion", exclusion_node)

# Define conditional route branching
graph.add_conditional_edges(
    "router",
    lambda state: state["route"],
    {
        "web": "scraper"
    }
)

# Web path
graph.add_edge("scraper", "cleaner")
graph.add_edge("cleaner", "html_extractor")
graph.add_edge("html_extractor", "llm_extractor")
graph.add_edge("llm_extractor", "exclusion")

# Set entry point
graph.set_entry_point("router")

# Compile graph
app = graph.compile()

# Optional: Run directly
if __name__ == "__main__":
    input_url = "https://www.bis.org/press/pressrels.htm"
    result = asyncio.run(app.ainvoke({
        "url": input_url,
        "scraper_input": {"url": input_url},
        "route": "web"
    }))
    print("\n✅ Final Output State:")
    print(result)
