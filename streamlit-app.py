import streamlit as st
import requests
import json
import pandas as pd
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
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

@st.cache_resource
def initialize_nltk():
    """Initialize NLTK resources"""
    try:
        nltk.download('punkt', quiet=True)
        nltk.download('vader_lexicon', quiet=True)
        return SentimentIntensityAnalyzer()
    except Exception as e:
        st.error(f"Error initializing NLTK: {str(e)}")
        return None

# Initialize NLTK and get sentiment analyzer
sia = initialize_nltk()

def simple_tokenize(text):
    """Simple sentence tokenization that works for multiple languages"""
    # Split on common sentence endings
    sentences = []
    current = ""
    
    for char in text:
        current += char
        if char in ['.', '!', '?'] and len(current.strip()) > 0:
            sentences.append(current.strip())
            current = ""
            
    if current.strip():
        sentences.append(current.strip())
        
    return sentences

def clean_text(text):
    """Clean and normalize text"""
    # Remove excessive whitespace
    text = ' '.join(text.split())
    # Remove very short lines (likely noise)
    lines = [line for line in text.split('\n') if len(line.strip()) > 30]
    return ' '.join(lines)

def scrape_url(url):
    """Scrape content from a URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Try to detect the encoding
        if 'charset' in response.headers.get('content-type', '').lower():
            response.encoding = response.apparent_encoding
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        
        # Get main content
        content = ""
        
        # Try to find main content area
        main_content = soup.find('main') or soup.find(id='content') or soup.find(class_='content')
        
        if main_content:
            paragraphs = main_content.find_all('p')
        else:
            paragraphs = soup.find_all('p')
        
        # Extract text from paragraphs
        content = ' '.join(p.get_text(strip=True) for p in paragraphs)
        
        return clean_text(content)
    except Exception as e:
        return f"Error scraping content: {str(e)}"

def analyze_content(text, language="en"):
    """Analyze the content of a text"""
    try:
        if not text or text.startswith("Error scraping content"):
            return {
                'summary': text if text else "No content available",
                'sentiment': {'compound': 0, 'neg': 0, 'neu': 1, 'pos': 0},
                'content_length': 0,
                'success': False
            }
        
        # Get sentiment scores
        sentiment = sia.polarity_scores(text)
        
        # Get summary using simple tokenization
        sentences = simple_tokenize(text)
        summary = ' '.join(sentences[:3]) if sentences else "No content available"
        
        return {
            'summary': summary,
            'sentiment': sentiment,
            'content_length': len(text),
            'success': True
        }
    except Exception as e:
        return {
            'summary': f"Error analyzing content: {str(e)}",
            'sentiment': {'compound': 0, 'neg': 0, 'neu': 1, 'pos': 0},
            'content_length': 0,
            'success': False
        }

# [Rest of the code remains the same as before...]
