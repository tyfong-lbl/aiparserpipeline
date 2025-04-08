from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

def run(playwright, url_test):
    browser = playwright.firefox.launch(headless=True)  # Run in headful mode #chromium
    context = browser.new_context(
    #     # viewport={"width": 1280, "height": 720},  # Set viewport size
    # This is my user agent for chromium when I launch in headful but it doesn't work in headless, even with "disable headless mode indicators" and "set extra headers" sections
        # user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"  
        user_agent = "Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0" ## THIS ONE IS WORKING IN HEADLESS FOR FIREFOX BROWSER! (either NT 10.0 or 11.0)
    #     # user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/109.0'
    )
    page = context.new_page()
    # page = browser.new_page()
    
    ## Disable headless mode indicators
    # page.add_init_script("""
    #     () => {
    #         Object.defineProperty(navigator, 'webdriver', {
    #             get: () => undefined,
    #         });
    #     }
    # """)
    # # # Set extra headers if necessary
    # page.set_extra_http_headers({
    #     "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    #     "accept-language": "en-US,en;q=0.9"
    # })

    try:
        page.goto(url_test, timeout=3000)
        # print(page.evaluate("() => navigator.userAgent"))
        print(page.title())
    except Exception as e:
        print(f"An error occurred: {e}")

    context.close()
    browser.close()

def run_stealth(playwright, url_test):
    browser = playwright.firefox.launch(headless=True)
    # context = browser.new_context(
    #     # viewport={"width": 1280, "height": 720},
    #     # user_agent = "Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0"
    #     # user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    #     user_agent ="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    # )
    # page = context.new_page()
    page = browser.new_page()

    # Apply stealth mode
    stealth_sync(page)

    try:
        page.goto(url_test, timeout=60000)
        print(page.title())
    except Exception as e:
        print(f"An error occurred in run_stealth: {e}")

    # context.close()
    browser.close()

with sync_playwright() as playwright:
    url = "https://www.nvenergy.com/about-nvenergy/news/news-releases/nv-energy-announces-largest-clean-energy-investment-in-nevadas-history"
    run(playwright, url)
    
    #"https://www.businesswire.com/news/home/20191113005485/en/Largest-Community-Solar-Project-in-Rhode-Island-Breaks-Ground-Adjacent-to-Superfund-Site-in-North-Smithfield"
    # run_stealth(playwright, url)