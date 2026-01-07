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

import os
import io
import json
import asyncio
import datetime
import argparse
from warcio import StatusAndHeaders, WARCWriter
from datetime import datetime, UTC
from playwright.async_api import async_playwright

OUTPUT="bwa_warc"
os.makedirs(OUTPUT, exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument('--data', type=json.loads)
args = parser.parse_args()

def fbasename(job):
    """
    Extract the filename from a job's URL hash.

    This function serves as a convenience accessor to retrieve the hexadecimal
    representation of a URL's hash value from a job object. The hash is used as
    a filename to uniquely identify and store archived web resources based on
    their source URL, ensuring consistent naming across the crawler system.

    :job: (dict) A job dictionary containing a 'url_hash' key with a 'hex' field.

    :return: str: The hexadecimal hash string to be used as a filename.
    """
    fn = job["url_hash"]["hex"]
    return fn

async def crawl_url_to_warc_object_async(url: str, timeout: int = 30000, user_agent: str = None):
    """
    Crawl a URL using Playwright's async API, record HAR, then convert that HAR
    into a WARC object in memory, ready to be written to a .warc.gz file.

    :param url: target URL
    :param timeout: max navigation timeout (ms)
    :param user_agent: optional user agent
    :return: an in-memory BufferWARCWriter
    """

    har_path = "temp_capture.har"

    # 1) Run Playwright async and record HAR
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context_args = {"record_har_path": har_path}
        if user_agent:
            context_args["user_agent"] = user_agent

        context = await browser.new_context(**context_args)
        page = await context.new_page()

        await page.goto(url, timeout=timeout)
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception:
            pass  # Ignore timeout, HAR may still be recorded

        await context.close()
        await browser.close()

    # 2) Load the HAR JSON
    if not os.path.exists(har_path):
        raise Exception(f"HAR file {har_path} not created, possibly due to navigation failure")
    with open(har_path, "r", encoding="utf-8") as f:
        har_data = json.load(f)

    # 3) Prepare an in-memory WARC writer
    warc_buffer = io.BytesIO()
    warc_writer = WARCWriter(warc_buffer, gzip=True)

    # 4) Convert HAR entries into WARC response records
    for entry in har_data.get("log", {}).get("entries", []):
        request = entry.get("request", {})
        response = entry.get("response", {})

        if not request.get("url"):
            continue

        # Skip entries missing response content
        content_info = response.get("content")
        if content_info is None:
            continue

        res_headers = [(h["name"], h["value"]) for h in response.get("headers", [])]

        # Build HTTP status line for WARC
        status_line = f"{response.get('status', '')} {response.get('statusText', '')}"

        http_headers = StatusAndHeaders(
            status_line,
            res_headers,
            protocol="HTTP/1.1"
        )

        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Convert the response body text into bytes
        body_text = content_info.get("text") or ""
        if content_info.get("encoding") == "base64":
            import base64
            body_bytes = base64.b64decode(body_text)
        else:
            body_bytes = body_text.encode("utf-8", errors="ignore")

        warc_record = warc_writer.create_warc_record(
            uri=request.get("url"),
            record_type="response",
            payload=io.BytesIO(body_bytes),
            http_headers=http_headers,
            warc_headers_dict={'WARC-Date': timestamp}
        )

        warc_writer.write_record(warc_record)

    warc_buffer.seek(0)
    os.remove(har_path)
    return warc_buffer

async def snapshot_warc(job,page):
    warc_buffer = await crawl_url_to_warc_object_async(page.url)
    with open(f"{OUTPUT}/{fbasename(job)}.warc.gz", "wb") as f:
        f.write(warc_buffer.getvalue())

async def snapshot_html(job,page):
    html = await page.content()
    with open(f"{OUTPUT}/{fbasename(job)}.html", "w") as f:
        f.write(html)

async def snapshot_image(job,page):
    await page.screenshot(path=f"{OUTPUT}/{fbasename(job)}.png", full_page=True)

def snapshot_job(job):
    with open(f"{OUTPUT}/{fbasename(job)}.json", "w") as f:
        f.write(json.dumps(job))

async def snapshot(job):
    url = job["url"]
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        
        try:
            # Navigate to the URL
            await page.goto(url)
            
            # snapshot logic follows
            await snapshot_warc(job, page)
            snapshot_job(job)
            await snapshot_html(job,page)
            await snapshot_image(job,page)
        
        finally:
            await browser.close()

if __name__ == "__main__":
    job = args.data
    asyncio.run(snapshot(job))
    print()
