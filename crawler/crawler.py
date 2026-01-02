from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import os

OUTPUT="crawler_output"
os.makedirs(OUTPUT, exist_ok=True)

def snapshot(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        html = page.content()
        domain = urlparse(url).netloc.replace(".", "_")
        with open(f"{OUTPUT}/{domain}.html", "w") as f:
            f.write(html)
        page.screenshot(path=f"{OUTPUT}/{domain}.png", full_page=True)
        browser.close()

if __name__ == "__main__":
    import sys
    snapshot(sys.argv[1])
