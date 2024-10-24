# ... [tidligere imports og setup forbliver det samme] ...

def get_sentiment_emoji(score):
    """Get emoji based on sentiment score"""
    if score > 0.05:
        return "🟢"  # Positiv
    elif score < -0.05:
        return "🔴"  # Negativ
    return "⚫️"  # Neutral

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
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get text from paragraphs
        paragraphs = soup.find_all('p')
        text = ' '.join(p.get_text().strip() for p in paragraphs)
        text = ' '.join(text.split())
        
        # Get sentiment
        sia = SentimentIntensityAnalyzer()
        sentiment = sia.polarity_scores(text)
        
        # Count words
        word_count = count_words(text)
        
        # Get summary (approximately 100 words)
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

def main():
    st.title("Google SERP Analyzer with Content Analysis")
    
    # Analysis mode selection
    analysis_mode = st.radio(
        "Vælg analyse mode:",
        ["SERP + Content Analysis", "SERP Only (med mulighed for at vælge URLs til analyse)"]
    )
    
    # ... [tidligere kode for land/sprog/antal resultater forbliver det samme] ...
    
    if st.button("Analyze"):
        if not search_phrases.strip():
            st.warning("Please enter at least one search phrase.")
            return
            
        phrases = [phrase.strip() for phrase in search_phrases.split("\n") if phrase.strip()]
        
        # Store results in session state for later use
        if 'search_results' not in st.session_state:
            st.session_state.search_results = {}
        
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
                
                # Store results in session state
                st.session_state.search_results[phrase] = df
                
                # Display basic results
                st.dataframe(df[["position", "title", "link", "snippet"]])
                
                if analysis_mode == "SERP + Content Analysis":
                    # Analyze all URLs immediately
                    st.subheader("Content Analysis")
                    
                    for _, row in df.iterrows():
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
                else:
                    # Allow selection of URLs to analyze
                    st.subheader("Select URLs to Analyze")
                    options = [f"#{row['position']} - {row['title']}" for idx, row in df.iterrows()]
                    selected_indices = st.multiselect(
                        "Choose URLs to analyze:",
                        options=range(len(options)),
                        format_func=lambda x: options[x]
                    )
                    
                    if selected_indices and st.button("Analyze Selected URLs"):
                        for idx in selected_indices:
                            row = df.iloc[idx]
                            analysis = scrape_and_analyze(row['link'])
                            sentiment_color = get_sentiment_color(analysis['sentiment'])
                            sentiment_emoji = get_sentiment_emoji(analysis['sentiment'])
                            
                            expander_label = f"{sentiment_emoji} #{row['position']} - {row['title']} ({row['link']})"
                            with st.expander(expander_label, expanded=True):
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
                
                st.success(f"Found {len(df)} results for '{phrase}'")
            else:
                st.warning(f"No results found or an error occurred for phrase: {phrase}")

if __name__ == "__main__":
    main()
