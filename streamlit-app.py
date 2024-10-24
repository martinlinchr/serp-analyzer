import streamlit as st
import requests
import json
import pandas as pd
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import time

# Download NLTK data
@st.cache_resource
def initialize_nltk():
    try:
        nltk.download('vader_lexicon', quiet=True)
    except:
        pass

initialize_nltk()

# Configuration dictionaries
COUNTRIES = {
    "us": "United States",
    "dk": "Danmark"
}

LANGUAGES = {
    "en": "English",
    "da": "Dansk"
}

# Sentiment analysis keywords
NEGATIVE_KEYWORDS = {
    "en": ["error", "mistake", "failure", "bad", "wrong", "poorly", "negative", "unfortunately", "problem", "issue"],
    "da": ["fejl", "dårlig", "forkert", "desværre", "problem", "negativt", "ikke god", "kritisk", "utilfreds", "mangel"]
}

POSITIVE_KEYWORDS = {
    "en": ["success", "excellent", "good", "best", "positive", "perfect", "recommend", "great", "innovative", "impressive"],
    "da": ["succes", "fremragende", "god", "bedste", "positiv", "perfekt", "anbefale", "fantastisk", "innovativ", "imponerende"]
}

def init_session_state():
    """Initialize session state variables"""
    if 'search_results' not in st.session_state:
        st.session_state.search_results = {}
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = {}
    if 'current_df' not in st.session_state:
        st.session_state.current_df = None
    if 'selected_urls' not in st.session_state:
        st.session_state.selected_urls = []

def get_sentiment_color(score):
    """Get color based on sentiment score"""
    if score > 0.05:
        return "rgba(0, 255, 0, 0.1)"  # Light green
    elif score < -0.05:
        return "rgba(255, 0, 0, 0.1)"  # Light red
    return "rgba(128, 128, 128, 0.1)"  # Light gray

def get_sentiment_emoji(score):
    """Get emoji based on sentiment score"""
    if score > 0.05:
        return "🟢"  # Positiv
    elif score < -0.05:
        return "🔴"  # Negativ
    return "⚫️"  # Neutral

def get_bypass_headers():
    """Get headers that help bypass some restrictions"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

class ContentAnalyzer:
    def __init__(self, language="en"):
        self.language = language
        self.sia = SentimentIntensityAnalyzer()
        
    def count_keywords(self, text, keyword_list):
        """Count occurrences of keywords in text"""
        text = text.lower()
        count = sum(text.count(keyword.lower()) for keyword in keyword_list)
        return count
    
    def analyze_text_quality(self, text):
        """Analyze text quality based on various metrics"""
        sentences = text.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        sentence_length_score = 1.0
        if avg_sentence_length < 5:
            sentence_length_score = 0.5
        elif avg_sentence_length > 40:
            sentence_length_score = 0.7
            
        return {
            'avg_sentence_length': avg_sentence_length,
            'sentence_length_score': sentence_length_score
        }
    
    def analyze_content(self, text):
        """Perform comprehensive content analysis"""
        sentiment = self.sia.polarity_scores(text)
        negative_count = self.count_keywords(text, NEGATIVE_KEYWORDS[self.language])
        positive_count = self.count_keywords(text, POSITIVE_KEYWORDS[self.language])
        quality_metrics = self.analyze_text_quality(text)
        
        total_words = len(text.split())
        keyword_ratio = (positive_count - negative_count) / total_words if total_words > 0 else 0
        
        combined_score = (
            sentiment['compound'] * 0.4 +
            keyword_ratio * 0.4 +
            quality_metrics['sentence_length_score'] * 0.2
        )
        
        return {
            'sentiment': sentiment,
            'keyword_analysis': {
                'positive_count': positive_count,
                'negative_count': negative_count,
                'keyword_ratio': keyword_ratio
            },
            'text_quality': quality_metrics,
            'combined_score': combined_score
        }

def scrape_with_retry(url, max_retries=3):
    """Attempt to scrape URL with multiple retries and methods"""
    headers = get_bypass_headers()
    session = requests.Session()
    
    for attempt in range(max_retries):
        try:
            response = session.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try to find and "click" accept buttons
                accept_buttons = soup.find_all(['button', 'a'], text=re.compile(r'accept|accept all|accepter|tillad', re.I))
                if accept_buttons:
                    response = session.get(url, headers=headers, timeout=15)
                
                return response.text
                
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(1)
    
    return None

def get_summary(text, word_count=100):
    """Get summary of approximately word_count words"""
    words = text.split()
    if len(words) <= word_count:
        return text
    
    summary_words = words[:word_count]
    return ' '.join(summary_words) + "..."

def count_words(text):
    """Count words in text"""
    return len(text.split())

def scrape_and_analyze(url, language="en"):
    """Scrape and analyze content from a URL"""
    try:
        content = scrape_with_retry(url)
        if not content:
            raise Exception("Could not retrieve content")
            
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        
        # Get text from paragraphs and other text elements
        text_elements = soup.find_all(['p', 'article', 'section', 'div'], class_=re.compile(r'text|content|article|body', re.I))
        if not text_elements:
            text_elements = soup.find_all('p')
            
        text = ' '.join(elem.get_text().strip() for elem in text_elements)
        text = ' '.join(text.split())
        
        # Analyze content
        analyzer = ContentAnalyzer(language)
        analysis_result = analyzer.analyze_content(text)
        
        return {
            'domain': urlparse(url).netloc,
            'summary': get_summary(text, 100),
            'sentiment': analysis_result['sentiment']['compound'],
            'sentiment_detailed': analysis_result['sentiment'],
            'keyword_analysis': analysis_result['keyword_analysis'],
            'text_quality': analysis_result['text_quality'],
            'combined_score': analysis_result['combined_score'],
            'content_length': len(text),
            'word_count': count_words(text),
            'success': True
        }
    except Exception as e:
        return {
            'domain': urlparse(url).netloc,
            'summary': f"Error: {str(e)}",
            'sentiment': 0,
            'sentiment_detailed': {'compound': 0, 'neg': 0, 'neu': 1, 'pos': 0},
            'keyword_analysis': {'positive_count': 0, 'negative_count': 0, 'keyword_ratio': 0},
            'text_quality': {'avg_sentence_length': 0, 'sentence_length_score': 0},
            'combined_score': 0,
            'content_length': 0,
            'word_count': 0,
            'success': False
        }

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

def display_analysis_results(row, language="en"):
    """Display analysis results for a single URL"""
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = {}
    
    # Check if we already have analysis for this URL
    if row['link'] in st.session_state.analysis_results:
        analysis = st.session_state.analysis_results[row['link']]
    else:
        analysis = scrape_and_analyze(row['link'], language)
        st.session_state.analysis_results[row['link']] = analysis
    
    sentiment_color = get_sentiment_color(analysis['combined_score'])
    sentiment_emoji = get_sentiment_emoji(analysis['combined_score'])
    
    expander_label = f"{sentiment_emoji} #{row['position']} - {row['title']}"
    with st.expander(expander_label, expanded=False):
        st.markdown(
            f"""
            <div style="padding: 10px; background-color: {sentiment_color}; border-radius: 5px;">
                <p><strong>URL:</strong> {row['link']}</p>
                <p><strong>Domain:</strong> {analysis['domain']}</p>
                <p><strong>Content Stats:</strong></p>
                <ul>
                    <li>Word Count: {analysis['word_count']} words</li>
                    <li>Character Count: {analysis['content_length']} characters</li>
                    <li>Average Sentence Length: {analysis['text_quality']['avg_sentence_length']:.1f} words</li>
                </ul>
                <p><strong>Content Analysis:</strong></p>
                <ul>
                    <li>Combined Score: {analysis['combined_score']:.2f}</li>
                    <li>VADER Sentiment: {analysis['sentiment']:.2f}</li>
                    <li>Positive Keywords: {analysis['keyword_analysis']['positive_count']}</li>
                    <li>Negative Keywords: {analysis['keyword_analysis']['negative_count']}</li>
                    <li>Keyword Ratio: {analysis['keyword_analysis']['keyword_ratio']:.2f}</li>
                </ul>
                <p><strong>Summary:</strong></p>
                <p>{analysis['summary']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

def analyze_all_urls(df):
    """Analyze all URLs in the DataFrame"""
    st.subheader("Content Analysis")
    
    for _, row in df.iterrows():
        display_analysis_results(row)

def analyze_selected_urls(df):
    """Allow user to select and analyze specific URLs"""
    st.subheader("Select URLs to Analyze")
    
    # Create a list of options with titles
    options = [f"#{row['position']} - {row['title']}" for _, row in df.iterrows()]
    
    # Maintain selected options in session state
    if 'selected_options' not in st.session_state:
        st.session_state.selected_options = []
    
    selected_options = st.multiselect(
        "Choose URLs to analyze:",
        options=options,
        default=st.session_state.selected_options
    )
    
    # Update session state
    st.session_state.selected_options = selected_options
    
    if selected_options:
        # Get the indices of selected options
        selected_indices = [options.index(opt) for opt in selected_options]
        
        # Display analysis for selected URLs
        for idx in selected_indices:
            row = df.iloc[idx]
            display_analysis_results(row)

def main():
    # Initialize session state
    init_session_state()
    
    st.title("Google SERP Analyzer with Content Analysis")
    
    # Analysis mode selection
    analysis_mode = st.radio(
        "Vælg analyse mode:",
        ["SERP + Content Analysis", "SERP Only (med mulighed for at vælge URLs til analyse)"]
    )
    
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
            results = get_all_serp_results(
                phrase,
                num_results=num_results,
                country=country,
                language=language
            )
            
            if results and "organic_results" in results:
                df = pd.DataFrame(results["organic_results"])
                df["position"] = range(1, len(df) + 1)
                
                # Store current results in session state
                st.session_state.current_df = df
                
                # Display basic results
                st.dataframe(df[["position", "title", "link", "snippet"]])
                
                if analysis_mode == "SERP + Content Analysis":
                    analyze_all_urls(df)
                else:
                    analyze_selected_urls(df)
                
                st.success(f"Found {len(df)} results for '{phrase}'")
            else:
                st.warning(f"No results found or an error occurred for phrase: {phrase}")

if __name__ == "__main__":
    main()
