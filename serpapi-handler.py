import streamlit as st
import requests

def get_serp_results(query, num_results=20, country="us", language="en", start=0):
    """Get SERP results with pagination"""
    if 'SERPAPI_KEY' not in st.secrets:
        st.error("SERPAPI_KEY not found in secrets.")
        st.stop()
    
    url = "https://serpapi.com/search.json"
    params = {
        "q": query,
        "num": 10,  # SerpAPI max per request
        "start": start,
        "engine": "google",
        "api_key": st.secrets.SERPAPI_KEY,
        "gl": country,
        "hl": language
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error making request to SERP API: {str(e)}")
        return None

def get_all_serp_results(query, num_results, country, language):
    """Get all SERP results using pagination"""
    all_results = []
    start = 0
    
    with st.spinner(f'Fetching search results...'):
        while len(all_results) < num_results:
            results = get_serp_results(query, 10, country, language, start)
            if not results or "organic_results" not in results:
                break
                
            all_results.extend(results["organic_results"])
            if len(results["organic_results"]) < 10:
                break
                
            start += 10
            
    return {"organic_results": all_results[:num_results]}
