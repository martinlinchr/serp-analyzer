import streamlit as st
import requests
import json
import pandas as pd

# Dictionary of country codes and their names
COUNTRIES = {
    "us": "United States",
    "uk": "United Kingdom",
    "au": "Australia",
    "ca": "Canada",
    "de": "Germany",
    "fr": "France",
    "es": "Spain",
    "it": "Italy",
    "jp": "Japan",
    "nl": "Netherlands",
    "br": "Brazil",
    "in": "India"
}

# Dictionary of language codes and their names
LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ja": "Japanese",
    "nl": "Dutch",
    "hi": "Hindi"
}

def get_serp_results(query, num_results=20, country="us", language="en"):
    # Get API key from Streamlit secrets
    if 'SERPAPI_KEY' not in st.secrets:
        st.error("SERPAPI_KEY not found in secrets. Please configure it in your .streamlit/secrets.toml file or Streamlit Cloud dashboard.")
        st.stop()
    
    url = "https://serpapi.com/search.json"
    params = {
        "q": query,
        "num": num_results,
        "engine": "google",
        "api_key": st.secrets.SERPAPI_KEY,
        "gl": country,  # Location parameter (country)
        "hl": language,  # Language parameter
        "google_domain": f"google.{country}"  # Google domain for the selected country
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error making request to SERP API: {str(e)}")
        return None

def main():
    st.title("Google SERP Top 20 Analyzer")
    
    # Create three columns for the input controls
    col1, col2, col3 = st.columns(3)
    
    # Country selection in first column
    with col1:
        country = st.selectbox(
            "Select Country",
            options=list(COUNTRIES.keys()),
            format_func=lambda x: COUNTRIES[x],
            help="Choose the country you want to emulate searches from"
        )
    
    # Language selection in second column
    with col2:
        language = st.selectbox(
            "Select Language",
            options=list(LANGUAGES.keys()),
            format_func=lambda x: LANGUAGES[x],
            help="Choose the language for search results"
        )
    
    # Number of results in third column
    with col3:
        num_results = st.number_input(
            "Number of Results",
            min_value=1,
            max_value=100,
            value=20,
            help="Choose how many results to fetch (max 100)"
        )
    
    search_phrases = st.text_area(
        "Enter search phrases (one per line):",
        help="Enter each search phrase on a new line"
    )
    
    if st.button("Analyze"):
        if not search_phrases.strip():
            st.warning("Please enter at least one search phrase.")
            return
            
        phrases = [phrase.strip() for phrase in search_phrases.split("\n") if phrase.strip()]
        
        # Display current settings
        st.info(f"Searching in {COUNTRIES[country]} ({country}) in {LANGUAGES[language]}")
        
        for phrase in phrases:
            st.subheader(f"Results for: {phrase}")
            results = get_serp_results(
                phrase,
                num_results=num_results,
                country=country,
                language=language
            )
            
            if results and "organic_results" in results:
                df = pd.DataFrame(results["organic_results"])
                st.dataframe(df[["position", "title", "link", "snippet"]])
            else:
                st.warning(f"No results found or an error occurred for phrase: {phrase}")

if __name__ == "__main__":
    main()
