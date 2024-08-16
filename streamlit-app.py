import streamlit as st
import requests
import json
import pandas as pd

# SerpAPI key (you should use environment variables for this in production)
SERPAPI_KEY = "your_serpapi_key_here"

def get_serp_results(query, num_results=20):
    url = "https://serpapi.com/search.json"
    params = {
        "q": query,
        "num": num_results,
        "engine": "google",
        "api_key": SERPAPI_KEY
    }
    response = requests.get(url, params=params)
    return response.json()

def main():
    st.title("Google SERP Top 20 Analyzer")
    
    search_phrases = st.text_area("Enter search phrases (one per line):")
    
    if st.button("Analyze"):
        phrases = [phrase.strip() for phrase in search_phrases.split("\n") if phrase.strip()]
        
        for phrase in phrases:
            st.subheader(f"Results for: {phrase}")
            results = get_serp_results(phrase)
            
            if "organic_results" in results:
                df = pd.DataFrame(results["organic_results"])
                st.dataframe(df[["position", "title", "link", "snippet"]])
            else:
                st.write("No results found or an error occurred.")

if __name__ == "__main__":
    main()
