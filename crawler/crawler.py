#********************************************************************************
#          ___  _     _ _                  _                 _                  *
#         / _ \| |   (_) |                | |               | |                 *
#        | (_) | |__  _| |_ __ _  ___  ___| | __  _ __   ___| |_                *
#         > _ <| '_ \| | __/ _` |/ _ \/ _ \ |/ / | '_ \ / _ \ __|               *
#        | (_) | |_) | | || (_| |  __/  __/   < _| | | |  __/ |_                *
#         \___/|_.__/|_|\__\__, |\___|\___|_|\_(_)_| |_|\___|\__|               *
#                           __/ |                                               *
#                          |___/                                                *
#                                                                               *
#*******************************************************************************/

from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

import os
import sys
import argparse
import json

OUTPUT="crawler_output"
os.makedirs(OUTPUT, exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument('--data', type=json.loads)
args = parser.parse_args()

def fbasename(job):
    fn = job["url_hash"]["hex"]
    return fn

def snapshot_html(job,page):
    html = page.content()
    with open(f"{OUTPUT}/{fbasename(job)}.html", "w") as f:
        f.write(html)

def snapshot_image(job,page):
    page.screenshot(path=f"{OUTPUT}/{fbasename(job)}.png", full_page=True)

def snapshot_job(job):
    with open(f"{OUTPUT}/{fbasename(job)}.json", "w") as f:
        f.write(json.dumps(job))

def snapshot(job):
     url = job["url"]
     with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        # domain = urlparse(url).netloc.replace(".", "_")
        domain = urlparse(url).netloc
        job["domain"] = domain
        snapshot_job(job)
        snapshot_html(job,page)
        snapshot_image(job,page)
        browser.close()
    
if __name__ == "__main__":
    job = args.data
    snapshot(job)
