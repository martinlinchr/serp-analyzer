import streamlit as st
import requests
from bs4 import BeautifulSoup
from typing import List
import time

def get_google_search_results(query: str, num_results: int = 20) -> List[dict]:
    url = f"https://www.google.com/search?q={query}&num={num_results}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    search_results = []
    for result in soup.select(".yuRUbf"):
        title = result.select_one("h3").text
        link = result.select_one("a")["href"]
        search_results.append({"title": title, "link": link})
    
    return search_results[:num_results]

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
