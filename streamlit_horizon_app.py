import streamlit as st
import pandas as pd
import os
import asyncio
from urllib.parse import urlparse
from pathlib import Path
from agents.router_agent import RouterAgent
from phase1_web_pipeline import app as langgraph_app

st.set_page_config(page_title="Regulatory Horizon Scanner", layout="wide")
st.title("📡 Regulatory Horizon Intelligence Platform")

url = st.text_input("Enter a regulatory website URL:")

if st.button("Run Phase 1"):
    if not url.strip():
        st.warning("⚠️ Please enter a valid URL.")
    else:
        with st.spinner("🔎 Routing the URL..."):
            router = RouterAgent()
            route_info = router.run({"url": url})
            route = route_info.get("route", "web")

        if route != "web":
            st.error("❌ RSS route is not yet supported. Please enter a website URL.")
        else:
            st.success("📬 Route selected: WEB (scraper pipeline)")

            with st.spinner("⚙️ Running Phase 1 pipeline..."):
                result = asyncio.run(langgraph_app.ainvoke({
                    "url": url,
                    "scraper_input": {"url": url},
                    "route": "web"
                }))

            # Search for output file
            parsed_domain = urlparse(url).netloc.replace(".", "_")
            search_folder = Path("regulatory_outputs/site_outputs")
            matched_files = sorted(
                search_folder.glob(f"{parsed_domain}_llm_exclusion_checked_*.xlsx"),
                key=os.path.getmtime,
                reverse=True
            )

            if matched_files:
                output_path = matched_files[0]
                df = pd.read_excel(output_path, engine="openpyxl")

                # ✅ Extract and render links from HYPERLINK formulas
                def extract_url_from_formula(cell):
                    if isinstance(cell, str) and cell.startswith('=HYPERLINK('):
                        try:
                            return cell.split('"')[1]
                        except IndexError:
                            return ""
                    return cell

                if "link" in df.columns:
                    df["Link"] = df["link"].apply(extract_url_from_formula)
                    df["Link"] = df["Link"].apply(
                        lambda x: f'<a href="{x}" target="_blank">Click here</a>' 
                        if pd.notna(x) and str(x).startswith("http") else ""
                    )
                    df.drop(columns=["link"], inplace=True)

                # Optional renaming for display clarity
                df.rename(columns={
                    "date": "Date",
                    "topic": "Topic",
                    "additional_context": "Context",
                    "regulator": "Regulator"
                }, inplace=True)

                st.success("✅ Phase 1 completed. Results below:")

                # ✅ Render HTML table with clickable links
                st.markdown(
                    df.to_html(escape=False, index=False),
                    unsafe_allow_html=True
                )

                # Optional styling
                st.markdown("""
                <style>
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        font-size: 14px;
                    }
                    th {
                        background-color: #f0f2f6;
                        text-align: center;
                        padding: 10px;
                    }
                    td {
                        padding: 8px;
                        vertical-align: top;
                    }
                </style>
                """, unsafe_allow_html=True)

                # Save to session
                st.session_state["phase1_df"] = df
                st.session_state["phase1_file"] = str(output_path)

                # Download button
                with open(output_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download Phase 1 Excel",
                        f.read(),
                        file_name=output_path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error("❌ Could not find or open Phase 1 output file.")
