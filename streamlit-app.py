import streamlit as st
import requests
import re
from html.parser import HTMLParser
from typing import List
import time

class GoogleResultParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_title = ""
        self.current_link = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "div" and ("class", "yuRUbf") in attrs:
            self.current_title = ""
            self.current_link = ""
        elif tag == "a" and self.current_link == "":
            for attr in attrs:
                if attr[0] == "href":
                    self.current_link = attr[1]
                    break
        elif tag == "h3":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "h3":
            self.in_title = False
        elif tag == "div" and self.current_title and self.current_link:
            self.results.append({"title": self.current_title, "link": self.current_link})

    def handle_data(self, data):
        if self.in_title:
            self.current_title += data

def get_google_search_results(query: str, num_results: int = 20) -> List[dict]:
    url = f"https://www.google.com/search?q={query}&num={num_results}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    parser = GoogleResultParser()
    parser.feed(response.text)
    
    return parser.results[:num_results]

def main():
    st.title("Google SERP Top 20 Analyzer")
    
    search_phrases = st.text_area("Enter search phrases (one per line):")
    
    if st.button("Analyze"):
        phrases = [phrase.strip() for phrase in search_phrases.split("\n") if phrase.strip()]
        
        for phrase in phrases:
            st.subheader(f"Results for: {phrase}")
            
            with st.spinner(f"Fetching results for '{phrase}'..."):
                results = get_google_search_results(phrase)
            
            st.write(f"Top {len(results)} results:")
            for i, result in enumerate(results, 1):
                st.write(f"{i}. [{result['title']}]({result['link']})")
            
            st.write("---")
            time.sleep(2)  # Add a delay to avoid hitting rate limits

if __name__ == "__main__":
    main()
