import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse
import streamlit as st

# Download NLTK data
@st.cache_resource
def initialize_nltk():
    try:
        nltk.download('vader_lexicon', quiet=True)
    except:
        pass

initialize_nltk()

def count_words(text):
    """Count words in text"""
    return len(text.split())

def get_summary(text, word_count=100):
    """Get summary of approximately word_count words"""
    words = text.split()
    if len(words) <= word_count:
        return text
    
    summary_words = words[:word_count]
    summary = ' '.join(summary_words) + "..."
    return summary

def scrape_and_analyze(url):
    """Scrape and analyze content from a URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        
        # Get text from paragraphs
        paragraphs = soup.find_all('p')
        text = ' '.join(p.get_text().strip() for p in paragraphs)
        text = ' '.join(text.split())
        
        # Get sentiment
        sia = SentimentIntensityAnalyzer()
        sentiment = sia.polarity_scores(text)
        
        # Count words
        word_count = count_words(text)
        
        # Get summary
        summary = get_summary(text, 100)
        
        return {
            'domain': urlparse(url).netloc,
            'summary': summary,
            'sentiment': sentiment['compound'],
            'sentiment_detailed': sentiment,
            'content_length': len(text),
            'word_count': word_count,
            'success': True
        }
    except Exception as e:
        return {
            'domain': urlparse(url).netloc,
            'summary': f"Error: {str(e)}",
            'sentiment': 0,
            'sentiment_detailed': {'compound': 0, 'neg': 0, 'neu': 1, 'pos': 0},
            'content_length': 0,
            'word_count': 0,
            'success': False
        }
