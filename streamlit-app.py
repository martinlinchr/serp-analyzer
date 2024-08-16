import streamlit as st
import requests
from html.parser import HTMLParser
from typing import List, Dict
import time
import json
import pandas as pd
from fpdf import FPDF
import base64
import traceback
import os

# ... [Previous code for GoogleResultParser and get_google_search_results remains the same] ...

def safe_export(export_func, data, filename):
    try:
        file_path = export_func(data, filename)
        return file_path, None
    except Exception as e:
        error_msg = f"Export failed: {str(e)}\n{traceback.format_exc()}"
        st.error(error_msg)
        return None, error_msg

def export_to_json(data: Dict[str, List[Dict[str, str]]], filename: str):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename

def export_to_excel(data: Dict[str, List[Dict[str, str]]], filename: str):
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        for query, results in data.items():
            df = pd.DataFrame(results)
            df.to_excel(writer, sheet_name=query[:31], index=False)  # Excel sheet names limited to 31 chars
    return filename

def export_to_pdf(data: Dict[str, List[Dict[str, str]]], filename: str):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    for query, results in data.items():
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"Results for: {query}", ln=1)
        pdf.set_font("Arial", size=12)
        for item in results:
            pdf.cell(0, 10, txt=item['title'][:80], ln=1)  # Limit title length
            pdf.cell(0, 10, txt=item['link'][:80], ln=1)  # Limit URL length
            pdf.multi_cell(0, 10, txt=item['description'][:200])  # Limit description length
            pdf.cell(0, 10, txt="-"*50, ln=1)
        pdf.add_page()
    
    pdf.output(filename)
    return filename

def get_download_link(file_path, file_name):
    with open(file_path, "rb") as file:
        contents = file.read()
    base64_encoded = base64.b64encode(contents).decode()
    return f'<a href="data:application/octet-stream;base64,{base64_encoded}" download="{file_name}">Download {file_name}</a>'

def main():
    st.title("Google SERP Top 20 Analyzer")
    
    search_phrases = st.text_area("Enter search phrases (one per line):")
    
    if st.button("Analyze"):
        phrases = [phrase.strip() for phrase in search_phrases.split("\n") if phrase.strip()]
        
        all_results = {}
        for phrase in phrases:
            st.subheader(f"Results for: {phrase}")
            
            with st.spinner(f"Fetching results for '{phrase}'..."):
                response_data = get_google_search_results(phrase)
            
            if "error" in response_data:
                st.error(f"Error occurred: {response_data['error']}")
                continue
            
            results = response_data["results"]
            debug_info = response_data["debug_info"]
            
            all_results[phrase] = results
            
            st.write(f"Top {len(results)} results:")
            if len(results) == 0:
                st.warning("No results found. Displaying debug information:")
                st.json(debug_info)
            else:
                for i, result in enumerate(results, 1):
                    st.write(f"{i}. {result.get('title', 'No title')}")
                    st.write(f"   URL: {result.get('link', 'No URL')}")
                    st.write(f"   Description: {result.get('description', 'No description')}")
                    st.write("---")
            
            time.sleep(2)  # Add a delay to avoid hitting rate limits
        
        # Export options
        if all_results:
            st.subheader("Export Results")
            export_format = st.selectbox("Choose export format:", ["JSON", "Excel", "PDF"])
            if st.button("Export"):
                with st.spinner("Exporting results..."):
                    if export_format == "JSON":
                        file_path, error = safe_export(export_to_json, all_results, "search_results.json")
                    elif export_format == "Excel":
                        file_path, error = safe_export(export_to_excel, all_results, "search_results.xlsx")
                    elif export_format == "PDF":
                        file_path, error = safe_export(export_to_pdf, all_results, "search_results.pdf")
                    
                    if file_path:
                        st.success(f"Export successful! Click below to download.")
                        st.markdown(get_download_link(file_path, os.path.basename(file_path)), unsafe_allow_html=True)
                    elif error:
                        st.error(f"Export failed. Error: {error}")

if __name__ == "__main__":
    main()
