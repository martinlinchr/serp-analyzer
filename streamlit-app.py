import streamlit as st
import requests
import json
import pandas as pd

def get_serp_results(query, num_results=20):
    # Get API key from Streamlit secrets
    if 'SERPAPI_KEY' not in st.secrets:
        st.error("SERPAPI_KEY not found in secrets. Please configure it in your .streamlit/secrets.toml file or Streamlit Cloud dashboard.")
        st.stop()
    
    url = "https://serpapi.com/search.json"
    params = {
        "q": query,
        "num": num_results,
        "engine": "google",
        "api_key": st.secrets.SERPAPI_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error making request to SERP API: {str(e)}")
        return None

def main():
    st.title("Google SERP Top 20 Analyzer")
    
    search_phrases = st.text_area("Enter search phrases (one per line):")
    
    if st.button("Analyze"):
        if not search_phrases.strip():
            st.warning("Please enter at least one search phrase.")
            return
            
        phrases = [phrase.strip() for phrase in search_phrases.split("\n") if phrase.strip()]
        
        for phrase in phrases:
            st.subheader(f"Results for: {phrase}")
            results = get_serp_results(phrase)
            
            if results and "organic_results" in results:
                df = pd.DataFrame(results["organic_results"])
                st.dataframe(df[["position", "title", "link", "snippet"]])
            else:
                st.warning(f"No results found or an error occurred for phrase: {phrase}")

if __name__ == "__main__":
    main()
