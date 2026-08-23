from bs4 import BeautifulSoup

def clean_text(text):
    if text is None:
        return None

    # Removes html tags AND removes HTML entities
    text = BeautifulSoup(text, "html.parser")
    cleaned_text1 = text.get_text()

    # Normalizes whitespace (splits on whitespace into a list, joins back together with a single space)
    return " ".join(cleaned_text1.split())

    
def clean_article(article):
    cleaned_copy = dict(article)
    cleaned_copy['summary'] = clean_text(article['summary']) if article['summary'] else None
    cleaned_copy['title'] = clean_text(article['title']) if article['title'] else None
    return cleaned_copy
