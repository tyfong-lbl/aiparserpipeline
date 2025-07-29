from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
# from bs4 import BeautifulSoup
import random

def scrape_articles(base_url, max_pages=5):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)  # Set headless=True for production
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0" 
            #'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = context.new_page()
        
        article_data = []
        current_page = 1

        while current_page <= max_pages:
            url = f"{base_url}page/{current_page}/" if current_page > 1 else base_url
            print(f"Scraping page {current_page}: {url}")
            
            try:
                page.goto(url, timeout=10000) #wait_until="networkidle",
            except PlaywrightTimeoutError:
                print(f"Timeout while loading page {current_page}. Continuing anyway.")
            
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            articles = soup.select('.td-module-title a, .entry-title a')
            print(f"Found {len(articles)} articles on page {current_page}")
            
            if not articles:
                print(f"No articles found on page {current_page}. Stopping.")
                break
            
            for article in articles:
                article_url = article['href']
                print(f"Attempting to scrape: {article_url}")
                
                article_page = context.new_page()
                try:
                    article_page.goto(article_url, timeout=60000)
                    article_content = article_page.inner_text('.td-post-content, .entry-content')
                    
                    if not article_content:
                        print(f"Failed to extract content for: {article_url}")
                        article_content = "Failed to extract article content"
                    
                except PlaywrightTimeoutError:
                    print(f"Timeout while loading article: {article_url}")
                    article_content = "Failed to load article content"
                
                article_data.append({
                    'title': article.text,
                    'url': article_url,
                    'content': article_content
                })
                
                article_page.close()
                time.sleep(random.uniform(1, 3))  # Random delay between requests
            
            current_page += 1
            
            next_page = soup.select_one('.next.page-numbers, a.next')
            if not next_page:
                print("No more pages available. Stopping.")
                break
            
            time.sleep(random.uniform(2, 5))  # Random delay between pages
       
        browser.close()
        return article_data

def scrape_url(base_url):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)  # Set headless=True for production
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0" 
            #'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = context.new_page()
        try:
            page.goto(base_url, timeout=6000) 
        except PlaywrightTimeoutError:
            print(f"Timeout while loading page. Continuing anyway.")
        title = page.title()
        text = page.evaluate('() => document.body.innerText')
        page.close()
        browser.close()
        return f"{title}.\n\n{text}"

# Run the scraper
# base_url =  'https://hub.jhu.edu/2022/08/03/skipjack-solar-center-now-operating/' #"https://pv-magazine-usa.com/category/installations/commercial-industrial-pv/"
base_url = "https://turningpoint-energy.com/our-clients/development-ri-king/" #"https://www.nvenergy.com/about-nvenergy/news/news-releases/nv-energy-announces-largest-clean-energy-investment-in-nevadas-history" #
# base_url = "https://www.blattnerenergy.com/newsroom/press-releases/engie-and-blattner-energy-give-back-to-local-school-in-abbott-texas"
# base_url =  "https://www.vasolarllc.com/project/nokesville-solar/" #"https://www.insidenova.com/news/business/prince-william-county-approves-30m-nokesville-solar-farm/article_695293aa-d208-11e8-b561-db3f32072c9f.html" #"https://www.nsenergybusiness.com/projects/athos-iii-solar-storage-project/" #"https://savionenergy.com/shikun-binui-acquire-savions-brazoria-west-solar-project-in-texas/"
# articles = scrape_articles(base_url, max_pages=3)  # Adjust max_pages as needed
urlcontents = scrape_url(base_url)
print(urlcontents)
# # Print or process the scraped data
# for i, article in enumerate(articles, 1):
#     print(f"Article {i}:")
#     print(f"Title: {article['title']}")
#     print(f"URL: {article['url']}")
#     print(f"Content: {article['content'][:200]}...")  # Print first 200 characters
#     print("\n---\n")

# print(f"Total articles scraped: {len(articles)}")
