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
import io
import sys
import argparse
import json
import asyncio
import datetime
import uuid
import requests
import logging
import urllib
from warcio.archiveiterator import WARCWriter

OUTPUT="bwa_snap"
os.makedirs(OUTPUT, exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument('--data', type=json.loads)
args = parser.parse_args()

def fbasename(job):
    fn = job["url_hash"]["hex"]
    return fn

def snapshot_warc(job,page):
    # fetch the page contents
    page_content = await page.content()

    # Create WARC writer
    output = io.BytesIO()
    writer = WARCWriter(output, logging=True)

    # Capture full page resources
    resources = await page.evaluate("""() => {
        return performance.getEntriesByType('resource')
            .map(resource => ({
                url: resource.name,
                type: resource.initiatorType
            }));
    }""")

   # Generate unique WARC record ID
    record_id = f'<urn:uuid:{uuid.uuid4()}>'
    
    # Write main page record
    record = writer.create_warc_record(
        page.url,
        'response',
        payload=io.BytesIO(page_content.encode('utf-8')),
        warc_headers_dict={
            'WARC-Record-ID': record_id,
            'WARC-Date': datetime.datetime.utcnow().isoformat(),
            'Content-Type': 'text/html'
        }
    )
    writer.write_record(record)
    
    # Capture additional resources
    for resource in resources:
        try:
            # Skip empty or invalid URLs
            if not resource.get('url'):
                continue
            
            # Validate URL
            parsed_url = urllib.parse.urlparse(resource['url'])
            if not parsed_url.scheme or not parsed_url.netloc:
                logging.warning(f"Invalid URL: {resource['url']}")
                continue
            
            # Fetch resource content with timeout and error handling
            try:
                resource_response = requests.get(
                    resource['url'], 
                    timeout=10,  # 10-second timeout
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    }
                )
                
                # Check for successful response
                resource_response.raise_for_status()
                
            except requests.RequestException as e:
                logging.error(f"Failed to fetch resource {resource['url']}: {e}")
                continue
            
            # Create WARC record for the resource
            resource_record = writer.create_warc_record(
                resource['url'],
                'resource',
                payload=io.BytesIO(resource_response.content),
                warc_headers_dict={
                    'WARC-Record-ID': f'<urn:uuid:{uuid.uuid4()}>',
                    'WARC-Date': datetime.datetime.utcnow().isoformat(),
                    'Content-Type': resource_response.headers.get('Content-Type', 'application/octet-stream')
                }
            )
            
            # Write the resource record to WARC
            writer.write_record(resource_record)
        
        except Exception as e:
            logging.error(f"Unexpected error processing resource {resource}: {e}")
            continue

    # Save WARC file
    with open(f"{OUTPUT}/{fbasename(job)}.html", 'wb') as warc_file:
        warc_file.write(output.getvalue())
        

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
        domain = urlparse(url).netloc
        job["domain"] = domain
        snapshot_job(job)
        snapshot_html(job,page)
        snapshot_image(job,page)
        snapshot_warc(job,page)
        browser.close()
    
if __name__ == "__main__":
    job = args.data
    snapshot(job)
