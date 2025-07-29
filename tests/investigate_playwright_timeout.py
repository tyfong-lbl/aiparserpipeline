import pandas as pd
import numpy as np
# import asyncio 
from playwright.async_api import async_playwright 

#### NOTE THIS CODE DOESN'T WORK

testurl = 'https://hub.jhu.edu/2022/08/03/skipjack-solar-center-now-operating/'

# playwright = await async_playwright().start()
# browser = await playwright.chromium.launch()

# page = await browser.new_page()
# await page.goto(testurl)
# title = await page.title()
# text = await page.evaluate('() => document.body.innerText')
# await page.close()

playwright = async_playwright().start()
# browser = playwright.chromium.launch()
browser = async_playwright().chromium.launch()
page = browser.new_page()
page.goto(testurl)
title = page.title()
text = page.evaluate('() => document.body.innerText')
page.close()
browser.close()

print(title)
print(text)
