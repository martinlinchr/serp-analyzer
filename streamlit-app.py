import streamlit as st
import requests
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
        self.debug_info = {"tags_found": []}

    def handle_starttag(self, tag, attrs):
        self.debug_info["tags_found"].append((tag, attrs))
        if tag == "div" and any(attr for attr in attrs if attr[0] == "class" and "g" in attr[1].split()):
            self.current_item = {}
        elif tag == "a" and not self.current_item.get("link"):
            for attr in attrs:
                if attr[0] == "href":
                    self.current_item["link"] = attr[1]
                    break
        elif tag == "h3":
            self.in_title = True
        elif tag == "div" and any(attr for attr in attrs if attr[0] == "class" and "VwiC3b" in attr[1].split()):
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

def get_google_search_results(query: str, num_results: int = 20) -> Dict[str, any]:
    url = f"https://www.google.com/search?q={query}&num={num_results}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
    except requests.RequestException as e:
        return {"error": f"Request failed: {str(e)}", "results": [], "debug_info": {}}
    
    parser = GoogleResultParser()
    parser.feed(response.text)
    
    return {
        "results": parser.results[:num_results],
        "debug_info": {
            "status_code": response.status_code,
            "content_length": len(response.text),
            "parser_debug": parser.debug_info
        }
    }

# ... [export functions remain the same] ...

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
        
        # ... [Export options remain the same] ...

if __name__ == "__main__":
    main()
