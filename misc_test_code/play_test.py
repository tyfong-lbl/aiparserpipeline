from playwright.sync_api import sync_playwright

def scrape_article(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        breakpoint()
        # Find the article content
        article_content = page.query_selector('div.post-content')
        if article_content:
            article_text = article_content.inner_text()
        else:
            # Fallback to finding the article content in the main body
            article_text = page.query_selector('body').inner_text()

        browser.close()
        return article_text

# Example usage
article_url = "https://pv-magazine-usa.com/2024/07/08/enphase-begins-shipping-u-s-made-microinverters-for-commercial-applications/"
article_content = scrape_article(article_url)
print(article_content)
