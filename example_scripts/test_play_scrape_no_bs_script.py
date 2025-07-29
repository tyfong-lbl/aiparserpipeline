from playwright.sync_api import sync_playwright

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

def scrape_article_list(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        # Find all the article links
        article_links = [link.get_attribute('href') for link in page.query_selector_all('article a')]

        articles = []
        for article_url in article_links:
            article_text = scrape_article(article_url)
            articles.append(article_text)

        browser.close()
        return articles

# Example usage
article_list_url = "https://pv-magazine-usa.com/category/installations/commercial-industrial-pv/"
article_contents = scrape_article_list(article_list_url)
for article in article_contents:
    print(article)
    print("---")
