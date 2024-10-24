import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from urllib.parse import urlparse

# Download NLTK data
try:
    nltk.download('vader_lexicon', quiet=True)
except:
    pass

# Dictionary of country codes and their names
COUNTRIES = {
    "us": "United States",
    "dk": "Danmark"
}

# Dictionary of language codes and their names
LANGUAGES = {
    "en": "English",
    "da": "Dansk"
}

def get_serp_results(query, num_results=20, country="us", language="en"):
    """Get SERP results"""
    if 'SERPAPI_KEY' not in st.secrets:
        st.error("SERPAPI_KEY not found in secrets.")
        st.stop()
    
    url = "https://serpapi.com/search.json"
    params = {
        "q": query,
        "num": num_results,
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

def scrape_and_analyze(url):
    """Scrape and analyze content from a URL"""
    try:
        # Setup headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Get the content
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get text from paragraphs
        paragraphs = soup.find_all('p')
        text = ' '.join(p.get_text().strip() for p in paragraphs)
        
        # Basic cleaning
        text = ' '.join(text.split())
        
        # Get sentiment
        sia = SentimentIntensityAnalyzer()
        sentiment = sia.polarity_scores(text)
        
        # Get summary (first 200 characters)
        summary = text[:200] + "..." if len(text) > 200 else text
        
        return {
            'domain': urlparse(url).netloc,
            'summary': summary,
            'sentiment': sentiment['compound'],
            'content_length': len(text),
            'success': True
        }
    except Exception as e:
        return {
            'domain': urlparse(url).netloc,
            'summary': f"Error: {str(e)}",
            'sentiment': 0,
            'content_length': 0,
            'success': False
        }

def main():
    st.title("Google SERP Analyzer with Content Analysis")
    
    # Create three columns for the input controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        country = st.selectbox(
            "Select Country",
            options=list(COUNTRIES.keys()),
            format_func=lambda x: COUNTRIES[x]
        )
    
    with col2:
        language = st.selectbox(
            "Select Language",
            options=list(LANGUAGES.keys()),
            format_func=lambda x: LANGUAGES[x]
        )
    
    with col3:
        num_results = st.number_input(
            "Number of Results",
            min_value=1,
            max_value=100,
            value=20
        )
    
    # Content analysis options
    col4, col5 = st.columns(2)
    
    with col4:
        analyze_content = st.checkbox("Analyze Content")
    
    with col5:
        if analyze_content:
            num_urls_to_analyze = st.number_input(
                "Number of URLs to Analyze",
                min_value=1,
                max_value=20,
                value=5
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
                
                # Add position if not present
                if "position" not in df.columns:
                    df["position"] = range(1, len(df) + 1)
                
                # Display basic results
                st.dataframe(df[["position", "title", "link", "snippet"]])
                
                # Content analysis if requested
                if analyze_content:
                    st.subheader("Content Analysis")
                    
                    # Analyze only the specified number of URLs
                    urls_to_analyze = df['link'].head(num_urls_to_analyze).tolist()
                    
                    # Create progress bar
                    progress_bar = st.progress(0)
                    
                    for i, url in enumerate(urls_to_analyze):
                        analysis = scrape_and_analyze(url)
                        
                        with st.expander(f"Analysis for result #{i+1}"):
                            st.write(f"**Domain:** {analysis['domain']}")
                            st.write(f"**Content Length:** {analysis['content_length']} characters")
                            
                            sentiment_score = analysis['sentiment']
                            sentiment_label = (
                                "Positive" if sentiment_score > 0.05
                                else "Negative" if sentiment_score < -0.05
                                else "Neutral"
                            )
                            
                            st.write(f"**Sentiment:** {sentiment_label} ({sentiment_score:.2f})")
                            st.write("**Summary:**")
                            st.write(analysis['summary'])
                        
                        # Update progress
                        progress_bar.progress((i + 1) / len(urls_to_analyze))
                    
                    progress_bar.empty()
                
                st.success(f"Found {len(df)} results for '{phrase}'")
            else:
                st.warning(f"No results found or an error occurred for phrase: {phrase}")

if __name__ == "__main__":
    main()
