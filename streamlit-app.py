import streamlit as st
import requests
import json
import pandas as pd
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

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

@st.cache_resource
def initialize_nltk():
    """Initialize NLTK resources"""
    nltk.download('punkt')
    nltk.download('vader_lexicon')
    return True

# Initialize NLTK
initialize_nltk()

def scrape_and_analyze_url(url):
    """
    Scrape content from a URL and analyze its content
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = ' '.join([p.get_text() for p in soup.find_all('p')])
        text = ' '.join(text.split())
        
        # Get domain
        domain = urlparse(url).netloc
        
        # Sentiment analysis
        sia = SentimentIntensityAnalyzer()
        sentiment_scores = sia.polarity_scores(text)
        
        # Create summary
        sentences = sent_tokenize(text)
        summary = ' '.join(sentences[:3]) if sentences else "No content available"
        
        return {
            'domain': domain,
            'summary': summary,
            'sentiment': sentiment_scores,
            'content_length': len(text),
            'success': True
        }
    except Exception as e:
        return {
            'domain': urlparse(url).netloc,
            'summary': f"Error scraping content: {str(e)}",
            'sentiment': {'compound': 0, 'neg': 0, 'neu': 0, 'pos': 0},
            'content_length': 0,
            'success': False
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
    except requests.exceptions.RequestException as e:
        st.error(f"Error making request to SERP API: {str(e)}")
        return None

def create_dataframe(results, analyze_content=False, num_urls_to_analyze=5):
    """Create DataFrame from results"""
    if not results or "organic_results" not in results:
        return None
        
    df = pd.DataFrame(results["organic_results"])
    
    # Add position if not present
    if "position" not in df.columns:
        df["position"] = range(1, len(df) + 1)
    
    # Ensure required columns exist
    for col in ["title", "link", "snippet"]:
        if col not in df.columns:
            df[col] = ""
    
    if analyze_content:
        with st.spinner(f'Analyzing content of top {num_urls_to_analyze} URLs...'):
            progress_bar = st.progress(0)
            
            urls_to_analyze = df['link'].head(num_urls_to_analyze).tolist()
            analyses = []
            
            for i, url in enumerate(urls_to_analyze):
                result = scrape_and_analyze_url(url)
                analyses.append(result)
                progress_bar.progress((i + 1) / len(urls_to_analyze))
            
            analysis_df = pd.DataFrame(analyses)
            
            # Merge with original DataFrame
            df = df.head(num_urls_to_analyze).copy()
            df['domain'] = analysis_df['domain']
            df['summary'] = analysis_df['summary']
            df['sentiment_compound'] = analysis_df['sentiment'].apply(lambda x: x['compound'])
            df['sentiment_category'] = df['sentiment_compound'].apply(
                lambda x: 'Positive' if x > 0.05 else ('Negative' if x < -0.05 else 'Neutral')
            )
            df['content_length'] = analysis_df['content_length']
            df['scraping_success'] = analysis_df['success']
    
    return df

def main():
    st.title("Google SERP Analyzer with Content Analysis")
    
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
    
    search_phrases = st.text_area("Enter search phrases (one per line):")
    
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
            
            df = create_dataframe(
                results,
                analyze_content=analyze_content,
                num_urls_to_analyze=num_urls_to_analyze if analyze_content else 0
            )
            
            if df is not None and not df.empty:
                if not analyze_content:
                    st.dataframe(df[["position", "title", "link", "snippet"]])
                else:
                    tab1, tab2 = st.tabs(["Basic Results", "Content Analysis"])
                    
                    with tab1:
                        st.dataframe(df[["position", "title", "link", "snippet"]])
                    
                    with tab2:
                        st.subheader("Sentiment Distribution")
                        sentiment_counts = df['sentiment_category'].value_counts()
                        st.bar_chart(sentiment_counts)
                        
                        st.subheader("Content Analysis Results")
                        for _, row in df.iterrows():
                            with st.expander(f"#{row['position']} - {row['title']}"):
                                st.write("**Domain:**", row['domain'])
                                st.write("**Sentiment:**", row['sentiment_category'])
                                st.write("**Sentiment Score:**", f"{row['sentiment_compound']:.2f}")
                                st.write("**Content Length:**", f"{row['content_length']} characters")
                                st.write("**Summary:**")
                                st.write(row['summary'])
                
                st.success(f"Found {len(df)} results for '{phrase}'")
            else:
                st.warning(f"No results found or an error occurred for phrase: {phrase}")

if __name__ == "__main__":
    main()
