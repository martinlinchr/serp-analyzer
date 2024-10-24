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
