
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
import datetime
from warcio import StatusAndHeaders, WARCWriter
from datetime import datetime, UTC
from playwright.async_api import async_playwright

class bwa_snapshot:
    
    async def snapshot_warc(job,page):
        warc_buffer = await crawl_url_to_warc_object_async(page.url)
        with open(f"{OUTPUT}/{hashed_basename(job)}.warc.gz", "wb") as f:
            f.write(warc_buffer.getvalue())

    async def snapshot_html(job,page):
        html = await page.content()
        with open(f"{OUTPUT}/{hashed_basename(job)}.html", "w") as f:
            f.write(html)

    async def snapshot_image(job,page):
        await page.screenshot(path=f"{OUTPUT}/{hashed_basename(job)}.png", full_page=True)

    def snapshot_job(job):
        with open(f"{OUTPUT}/{hashed_basename(job)}.json", "w") as f:
            f.write(json.dumps(job))

