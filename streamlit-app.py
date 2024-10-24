import streamlit as st
import pandas as pd
from serpapi_handler import get_all_serp_results
from content_analyzer import scrape_and_analyze
from utils import get_sentiment_color, get_sentiment_emoji

# Configuration dictionaries
COUNTRIES = {
    "us": "United States",
    "dk": "Danmark"
}

LANGUAGES = {
    "en": "English",
    "da": "Dansk"
}

def main():
    st.title("Google SERP Analyzer with Content Analysis")
    
    # Analysis mode selection
    analysis_mode = st.radio(
        "Vælg analyse mode:",
        ["SERP + Content Analysis", "SERP Only (med mulighed for at vælge URLs til analyse)"]
    )
    
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
                
                # Display basic results
                st.dataframe(df[["position", "title", "link", "snippet"]])
                
                if analysis_mode == "SERP + Content Analysis":
                    analyze_all_urls(df)
                else:
                    analyze_selected_urls(df)
                
                st.success(f"Found {len(df)} results for '{phrase}'")
            else:
                st.warning(f"No results found or an error occurred for phrase: {phrase}")

def analyze_all_urls(df):
    """Analyze all URLs in the DataFrame"""
    st.subheader("Content Analysis")
    
    for _, row in df.iterrows():
        display_analysis_results(row)

def analyze_selected_urls(df):
    """Allow user to select and analyze specific URLs"""
    st.subheader("Select URLs to Analyze")
    options = [f"#{row['position']} - {row['title']}" for _, row in df.iterrows()]
    selected_indices = st.multiselect(
        "Choose URLs to analyze:",
        options=range(len(options)),
        format_func=lambda x: options[x]
    )
    
    if selected_indices and st.button("Analyze Selected URLs"):
        for idx in selected_indices:
            row = df.iloc[idx]
            display_analysis_results(row)

def display_analysis_results(row):
    """Display analysis results for a single URL"""
    analysis = scrape_and_analyze(row['link'])
    sentiment_color = get_sentiment_color(analysis['sentiment'])
    sentiment_emoji = get_sentiment_emoji(analysis['sentiment'])
    
    expander_label = f"{sentiment_emoji} #{row['position']} - {row['title']} ({row['link']})"
    with st.expander(expander_label, expanded=False):
        st.markdown(
            f"""
            <div style="padding: 10px; background-color: {sentiment_color}; border-radius: 5px;">
                <p><strong>Domain:</strong> {analysis['domain']}</p>
                <p><strong>Content Stats:</strong></p>
                <ul>
                    <li>Word Count: {analysis['word_count']} words</li>
                    <li>Character Count: {analysis['content_length']} characters</li>
                </ul>
                <p><strong>Sentiment Scores:</strong></p>
                <ul>
                    <li>Overall: {analysis['sentiment']:.2f}</li>
                    <li>Positive: {analysis['sentiment_detailed']['pos']:.2f}</li>
                    <li>Neutral: {analysis['sentiment_detailed']['neu']:.2f}</li>
                    <li>Negative: {analysis['sentiment_detailed']['neg']:.2f}</li>
                </ul>
                <p><strong>Summary:</strong></p>
                <p>{analysis['summary']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
