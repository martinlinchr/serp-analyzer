import streamlit as st
import requests
import json
import pandas as pd
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize
from bs4 import BeautifulSoup
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

# Download NLTK data to user's home directory
@st.cache_resource
def initialize_nltk():
    nltk.download('punkt', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
    return SentimentIntensityAnalyzer()

# Initialize NLTK and get sentiment analyzer
sia = initialize_nltk()

def clean_text(text):
    """Clean and normalize text"""
    return ' '.join(text.split())

def scrape_url(url):
    """Scrape content from a URL"""
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
        
        # Get text from paragraphs
        paragraphs = soup.find_all('p')
        text = ' '.join(p.get_text() for p in paragraphs)
        return clean_text(text)
    except Exception as e:
        return f"Error scraping content: {str(e)}"

def analyze_content(text):
    """Analyze the content of a text"""
    try:
        # Get sentiment scores
        sentiment = sia.polarity_scores(text)
        
        # Get summary (first 3 sentences)
        sentences = sent_tokenize(text)
        summary = ' '.join(sentences[:3]) if sentences else "No content available"
        
        return {
            'summary': summary,
            'sentiment': sentiment,
            'content_length': len(text)
        }
    except Exception as e:
        return {
            'summary': f"Error analyzing content: {str(e)}",
            'sentiment': {'compound': 0, 'neg': 0, 'neu': 0, 'pos': 0},
            'content_length': 0
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

def create_dataframe(results, analyze_content_flag=False, num_urls_to_analyze=5):
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
    
    if analyze_content_flag:
        df = df.head(num_urls_to_analyze).copy()
        
        analysis_results = []
        total = len(df)
        
        progress_bar = st.progress(0)
        for index, row in df.iterrows():
            try:
                with st.spinner(f'Analyzing content from {row["domain"] if "domain" in row else row["link"]}...'):
                    # Scrape content
                    content = scrape_url(row['link'])
                    
                    # Analyze content
                    analysis = analyze_content(content)
                    
                    analysis['domain'] = urlparse(row['link']).netloc
                    analysis['success'] = True
                    
            except Exception as e:
                analysis = {
                    'domain': urlparse(row['link']).netloc,
                    'summary': f"Error: {str(e)}",
                    'sentiment': {'compound': 0, 'neg': 0, 'neu': 0, 'pos': 0},
                    'content_length': 0,
                    'success': False
                }
                
            analysis_results.append(analysis)
            progress_bar.progress((index + 1) / total)
        
        # Add analysis results to DataFrame
        df['domain'] = [r['domain'] for r in analysis_results]
        df['summary'] = [r['summary'] for r in analysis_results]
        df['sentiment_compound'] = [r['sentiment']['compound'] for r in analysis_results]
        df['sentiment_category'] = df['sentiment_compound'].apply(
            lambda x: 'Positive' if x > 0.05 else ('Negative' if x < -0.05 else 'Neutral')
        )
        df['content_length'] = [r['content_length'] for r in analysis_results]
        df['scraping_success'] = [r['success'] for r in analysis_results]
    
    return df

def main():
    st.title("Google SERP Analyzer with Content Analysis")
    
    # Create columns for input controls
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
        analyze_content_flag = st.checkbox("Analyze Content")
    
    with col5:
        if analyze_content_flag:
            num_urls_to_analyze = st.number_input(
                "Number of URLs to Analyze",
                min_value=1,
                max_value=20,
                value=5
            )
        else:
            num_urls_to_analyze = 0
    
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
            
            if not results:
                st.error("Failed to get search results.")
                continue
                
            df = create_dataframe(
                results,
                analyze_content_flag=analyze_content_flag,
                num_urls_to_analyze=num_urls_to_analyze
            )
            
            if df is not None and not df.empty:
                if not analyze_content_flag:
                    st.dataframe(df[["position", "title", "link", "snippet"]])
                else:
                    tab1, tab2 = st.tabs(["Basic Results", "Content Analysis"])
                    
                    with tab1:
                        st.dataframe(df[["position", "title", "link", "snippet"]])
                    
                    with tab2:
                        # Show sentiment distribution
                        st.subheader("Sentiment Distribution")
                        sentiment_counts = df['sentiment_category'].value_counts()
                        st.bar_chart(sentiment_counts)
                        
                        # Show detailed analysis
                        st.subheader("Content Analysis Results")
                        for _, row in df.iterrows():
                            with st.expander(f"#{row['position']} - {row['title']}"):
                                if row['scraping_success']:
                                    st.write("**Domain:**", row['domain'])
                                    st.write("**Sentiment:**", row['sentiment_category'])
                                    st.write("**Sentiment Score:**", f"{row['sentiment_compound']:.2f}")
                                    st.write("**Content Length:**", f"{row['content_length']} characters")
                                    st.write("**Summary:**")
                                    st.write(row['summary'])
                                else:
                                    st.error("Failed to analyze this URL")
                
                st.success(f"Found {len(df)} results for '{phrase}'")
            else:
                st.warning(f"No results found for phrase: {phrase}")

if __name__ == "__main__":
    main()
