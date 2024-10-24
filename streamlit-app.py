import streamlit as st
import requests
import json
import pandas as pd

# Dictionary of country codes and their names
COUNTRIES = {
    "us": "United States",
    "dk": "Danmark"  # Changed from "da" to "dk"
}

# Dictionary of language codes and their names
LANGUAGES = {
    "en": "English",
    "da": "Dansk"  # Language code remains "da" for Danish
}

def get_serp_results(query, num_results=20, country="us", language="en"):
    """
    Get SERP results with pagination support and error handling
    """
    if 'SERPAPI_KEY' not in st.secrets:
        st.error("SERPAPI_KEY not found in secrets. Please configure it in your .streamlit/secrets.toml file or Streamlit Cloud dashboard.")
        st.stop()
    
    all_results = []
    remaining_results = num_results
    start_offset = 0
    
    while remaining_results > 0:
        # Calculate how many results to request in this batch (max 100 per request)
        batch_size = min(remaining_results, 100)
        
        url = "https://serpapi.com/search.json"
        params = {
            "q": query,
            "num": batch_size,
            "start": start_offset,
            "engine": "google",
            "api_key": st.secrets.SERPAPI_KEY,
            "gl": country,
            "hl": language
        }
        
        try:
            with st.spinner(f'Fetching results {start_offset + 1} to {start_offset + batch_size}...'):
                response = requests.get(url, params=params)
                response.raise_for_status()
                
                results = response.json()
                
                # Check if we have the pagination info
                if "serpapi_pagination" in results:
                    st.info(f"Page {results['serpapi_pagination'].get('current', 1)} of results")
                
                if "organic_results" in results:
                    all_results.extend(results["organic_results"])
                    
                    # If we got fewer results than requested, we've hit the end
                    if len(results["organic_results"]) < batch_size:
                        st.warning(f"Only {len(all_results)} results available.")
                        break
                        
                    # Update counters for next iteration
                    remaining_results -= batch_size
                    start_offset += batch_size
                else:
                    st.warning(f"No more results available after {len(all_results)} results.")
                    break
                
        except requests.exceptions.RequestException as e:
            st.error(f"Error making request to SERP API: {str(e)}")
            if hasattr(e.response, 'text'):
                st.error(f"API Response: {e.response.text}")
            break
    
    # Create final results structure
    final_results = {
        "organic_results": all_results[:num_results]  # Ensure we don't return more than requested
    }
    
    return final_results

def create_dataframe(results):
    """
    Create a DataFrame from results with proper column handling
    """
    if not results or "organic_results" not in results:
        return None
        
    df = pd.DataFrame(results["organic_results"])
    
    # Define required columns and their default values
    required_columns = {
        "position": range(1, len(df) + 1),
        "title": "",
        "link": "",
        "snippet": ""
    }
    
    # Add missing columns with default values
    for col, default in required_columns.items():
        if col not in df.columns:
            if col == "position":
                df[col] = required_columns["position"]
            else:
                df[col] = default
    
    return df

def main():
    st.title("Google SERP Analyzer")
    
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
            
            df = create_dataframe(results)
            
            if df is not None and not df.empty:
                st.dataframe(df[["position", "title", "link", "snippet"]])
                st.success(f"Found {len(df)} results for '{phrase}'")
            else:
                st.warning(f"No results found or an error occurred for phrase: {phrase}")

if __name__ == "__main__":
    main()
