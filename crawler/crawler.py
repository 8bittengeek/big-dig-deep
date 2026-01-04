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
import asyncio
from playwright.async_api import async_playwright
from warcio import WARCWriter
from warcio import StatusAndHeaders
import httpx  # Recommended for async HTTP requests
from datetime import datetime, UTC

OUTPUT="bwa_snap"
os.makedirs(OUTPUT, exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument('--data', type=json.loads)
args = parser.parse_args()

def fbasename(job):
    fn = job["url_hash"]["hex"]
    return fn

async def snapshot_warc(job,page):
    """
    Captures a webpage snapshot and saves it as a WARC (Web ARChive) file.
    This function fetches the main page content and all associated resources,
    then writes them to a WARC format file for archival purposes.
    Args:
        job: Job object containing metadata about the crawl job.
        page: Playwright page object representing the webpage to capture.
    Returns:
        None
    Raises:
        Exception: Any unexpected errors during resource processing are logged
                   and skipped without stopping execution.
    Notes:
        - The function captures the main HTML page and all resource entries
          from the browser's performance API.
        - Each resource is fetched with a 10-second timeout and validated
          before being added to the WARC file.
        - Invalid or failed resource fetches are logged as warnings/errors
          but do not interrupt the overall archival process.
        - Output file is saved to OUTPUT directory with .warc extension
          based on the job filename.
    Implementation Details:
        - Uses WARCWriter to create WARC-compliant records
        - Generates unique record IDs using UUID v4
        - Includes HTTP User-Agent header for resource requests
        - Validates URLs using urllib.parse.urlparse()
    """
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
    with open(f"{OUTPUT}/{fbasename(job)}.warc", 'wb') as warc_file:
        warc_file.write(output.getvalue())
        

async def snapshot(job):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        
        try:
            await page.goto(job['url'])
            await snapshot_warc(job, page)
        finally:
            await browser.close()

async def snapshot_html(job,page):
    html = await page.content()
    with open(f"{OUTPUT}/{fbasename(job)}.html", "w") as f:
        f.write(html)

async def snapshot_image(job,page):
    await page.screenshot(path=f"{OUTPUT}/{fbasename(job)}.png", full_page=True)

async def snapshot_job(job):
    with open(f"{OUTPUT}/{fbasename(job)}.json", "w") as f:
        f.write(json.dumps(job))

async def _snapshot(job):
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
        await snapshot_warc(job,page)
        browser.close()

async def snapshot(job):
    url = job["url"]
    domain = urlparse(url).netloc
    job["domain"] = domain
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        
        try:
            # Navigate to the URL
            await page.goto(url)
            
            # snapshot logic follows
            await snapshot_warc(job, page)
            await snapshot_job(job)
            await snapshot_html(job,page)
            await snapshot_image(job,page)
        
        finally:
            await browser.close()

if __name__ == "__main__":
    job = args.data
    asyncio.run(snapshot(job))
