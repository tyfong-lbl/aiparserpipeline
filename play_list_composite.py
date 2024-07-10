from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
from bs4 import BeautifulSoup
import random
import pandas as pd

def get_article_urls(base_url, max_pages=5):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Set headless=True for production
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = context.new_page()
        
        articles_data = []
        current_page = 1

        while current_page <= max_pages:
            url = f"{base_url}page/{current_page}/" if current_page > 1 else base_url
            print(f"Scraping page {current_page}: {url}")
            
            try:
                page.goto(url, wait_until="networkidle", timeout=5000)
            except PlaywrightTimeoutError:
                print(f"Timeout while loading page {current_page}. Continuing anyway.")
            
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            articles = soup.select('.td-module-title a, .entry-title a')
            print(f"Found {len(articles)} articles on page {current_page}")
            articles_data.extend(articles)            

            if not articles:
                print(f"No articles found on page {current_page}. Stopping.")
                break
            current_page += 1

        return articles_data
        

def scrape_article(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        # Find the article content
        article_content = page.query_selector('div.post-content')
        if article_content:
            article_text = article_content.inner_text()
        else:
            # Fallback to finding the article content in the main body
            article_text = page.query_selector('body').inner_text()

        browser.close()
        return article_text
    
def get_all_articles(article_urls):
    rows = []
    for article in article_urls:
                article_url = article['href']
                article_body = scrape_article(article_url)
                article_title = article.text
                rows.append({'url':article_url,
                     'title': article_title,
                     'text': article_body})
    df = pd.DataFrame(rows)
    return rows




     
article_list_url = "https://pv-magazine-usa.com/category/installations/commercial-industrial-pv/"
article_urls = get_article_urls(article_list_url, max_pages=2)

output = get_all_articles(article_urls)
breakpoint()