import streamlit as st
import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize
from concurrent.futures import ThreadPoolExecutor
import time
from requests.exceptions import RequestException
from urllib.parse import urlparse

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('punkt')
    nltk.download('vader_lexicon')

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

def scrape_and_analyze_url(url):
    """
    Scrape content from a URL and analyze its content
    """
    try:
        # Add headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = ' '.join([p.get_text() for p in soup.find_all('p')])
        
        # Clean up text
        text = ' '.join(text.split())
        
        # Get domain
        domain = urlparse(url).netloc
        
        # Perform sentiment analysis
        sia = SentimentIntensityAnalyzer()
        sentiment_scores = sia.polarity_scores(text)
        
        # Create summary (simple version using first 3 sentences)
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
                
                if "organic_results" in results:
                    all_results.extend(results["organic_results"])
                    if len(results["organic_results"]) < batch_size:
                        break
                    remaining_results -= batch_size
                    start_offset += batch_size
                else:
                    break
                
        except requests.exceptions.RequestException as e:
            st.error(f"Error making request to SERP API: {str(e)}")
            break
    
    return {"organic_results": all_results[:num_results]}

def create_dataframe(results, analyze_content=False, num_urls_to_analyze=5):
    """
    Create a DataFrame from results with content analysis
    """
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
        # Show progress bar for content analysis
        with st.spinner(f'Analyzing content of top {num_urls_to_analyze} URLs...'):
            # Create progress bar
            progress_bar = st.progress(0)
            
            # Analyze only the specified number of URLs
            urls_to_analyze = df['link'].head(num_urls_to_analyze).tolist()
            
            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_url = {executor.submit(scrape_and_analyze_url, url): url for url in urls_to_analyze}
                
                # Store results
                analyses = []
                for i, future in enumerate(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        analyses.append(result)
                    except Exception as e:
                        analyses.append({
                            'domain': urlparse(url).netloc,
                            'summary': f"Error: {str(e)}",
                            'sentiment': {'compound': 0, 'neg': 0, 'neu': 0, 'pos': 0},
                            'content_length': 0,
                            'success': False
                        })
                    # Update progress bar
                    progress_bar.progress((i + 1) / len(urls_to_analyze))
            
            # Create analysis DataFrame
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
            format_func=lambda x: COUNTRIES[x],
            help="Choose the country you want to emulate searches from"
        )
    
    with col2:
        language = st.selectbox(
            "Select Language",
            options=list(LANGUAGES.keys()),
            format_func=lambda x: LANGUAGES[x],
            help="Choose the language for search results"
        )
    
    with col3:
        num_results = st.number_input(
            "Number of Results",
            min_value=1,
            max_value=100,
            value=20,
            help="Choose how many results to fetch (max 100)"
        )
    
    # Add content analysis options
    col4, col5 = st.columns(2)
    
    with col4:
        analyze_content = st.checkbox(
            "Analyze Content",
            help="Scrape and analyze the content of the top results"
        )
    
    with col5:
        if analyze_content:
            num_urls_to_analyze = st.number_input(
                "Number of URLs to Analyze",
                min_value=1,
                max_value=20,
                value=5,
                help="Choose how many URLs to analyze (max 20)"
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
        
        st.info(f"Searching in {COUNTRIES[country]} ({country}) in {LANGUAGES[language]}")
        
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
                # Display basic results
                if not analyze_content:
                    st.dataframe(df[["position", "title", "link", "snippet"]])
                else:
                    # Create tabs for different views
                    tab1, tab2 = st.tabs(["Basic Results", "Content Analysis"])
                    
                    with tab1:
                        st.dataframe(df[["position", "title", "link", "snippet"]])
                    
                    with tab2:
                        # Display sentiment distribution
                        sentiment_counts = df['sentiment_category'].value_counts()
                        st.subheader("Sentiment Distribution")
                        st.bar_chart(sentiment_counts)
                        
                        # Display detailed content analysis
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
