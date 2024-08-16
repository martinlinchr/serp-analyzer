import streamlit as st
import requests
import re
from html.parser import HTMLParser
from typing import List, Dict
import time
import json
import pandas as pd
from fpdf import FPDF

class GoogleResultParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_item = {}
        self.in_title = False
        self.in_snippet = False

    def handle_starttag(self, tag, attrs):
        if tag == "div" and ("class", "yuRUbf") in attrs:
            self.current_item = {}
        elif tag == "a" and not self.current_item.get("link"):
            for attr in attrs:
                if attr[0] == "href":
                    self.current_item["link"] = attr[1]
                    break
        elif tag == "h3":
            self.in_title = True
        elif tag == "div" and ("class", "VwiC3b") in attrs:
            self.in_snippet = True

    def handle_endtag(self, tag):
        if tag == "h3":
            self.in_title = False
        elif tag == "div" and self.in_snippet:
            self.in_snippet = False
            if self.current_item and len(self.current_item) == 3:
                self.results.append(self.current_item)
                self.current_item = {}

    def handle_data(self, data):
        if self.in_title and not self.current_item.get("title"):
            self.current_item["title"] = data.strip()
        elif self.in_snippet and not self.current_item.get("description"):
            self.current_item["description"] = data.strip()

def get_google_search_results(query: str, num_results: int = 20) -> List[Dict[str, str]]:
    url = f"https://www.google.com/search?q={query}&num={num_results}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    parser = GoogleResultParser()
    parser.feed(response.text)
    
    return parser.results[:num_results]

def export_to_json(data: List[Dict[str, str]], filename: str):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def export_to_excel(data: List[Dict[str, str]], filename: str):
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)

def export_to_pdf(data: List[Dict[str, str]], filename: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    for item in data:
        pdf.cell(200, 10, txt=item['title'], ln=1)
        pdf.cell(200, 10, txt=item['link'], ln=1)
        pdf.multi_cell(0, 10, txt=item['description'])
        pdf.cell(200, 10, txt="-"*50, ln=1)
    
    pdf.output(filename)

def main():
    st.title("Google SERP Top 20 Analyzer")
    
    search_phrases = st.text_area("Enter search phrases (one per line):")
    
    if st.button("Analyze"):
        phrases = [phrase.strip() for phrase in search_phrases.split("\n") if phrase.strip()]
        
        all_results = {}
        for phrase in phrases:
            st.subheader(f"Results for: {phrase}")
            
            with st.spinner(f"Fetching results for '{phrase}'..."):
                results = get_google_search_results(phrase)
            
            all_results[phrase] = results
            
            st.write(f"Top {len(results)} results:")
            for i, result in enumerate(results, 1):
                st.write(f"{i}. {result['title']}")
                st.write(f"   URL: {result['link']}")
                st.write(f"   Description: {result['description']}")
                st.write("---")
            
            time.sleep(2)  # Add a delay to avoid hitting rate limits
        
        # Export options
        st.subheader("Export Results")
        export_format = st.selectbox("Choose export format:", ["JSON", "Excel", "PDF"])
        if st.button("Export"):
            if export_format == "JSON":
                export_to_json(all_results, "search_results.json")
                st.success("Exported to search_results.json")
            elif export_format == "Excel":
                export_to_excel([item for sublist in all_results.values() for item in sublist], "search_results.xlsx")
                st.success("Exported to search_results.xlsx")
            elif export_format == "PDF":
                export_to_pdf([item for sublist in all_results.values() for item in sublist], "search_results.pdf")
                st.success("Exported to search_results.pdf")

if __name__ == "__main__":
    main()
