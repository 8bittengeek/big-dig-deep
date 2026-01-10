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

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import BackgroundTasks
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from crawler.bwa_crawl import crawler
from crawler.bwa_jobqueue import job_queue

import os
import subprocess
import logging
import json
import hashlib


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs = job_queue()

class ArchiveRequest(BaseModel):
    url: str
    depth: int
    assets: bool


def url_key(canonical_url: str) -> str:
    return "url-sha256:" + hashlib.sha256(
        canonical_url.encode("utf-8")
    ).hexdigest()


def normalize_url(url: str) -> str:
    u = urlparse(url.strip())

    scheme = u.scheme.lower() or "http"
    netloc = u.hostname.lower()

    # strip default ports
    if u.port and not (
        (scheme == "http" and u.port == 80) or
        (scheme == "https" and u.port == 443)
    ):
        netloc += f":{u.port}"

    path = u.path or "/"

    # sort query params
    query = urlencode(sorted(parse_qsl(u.query, keep_blank_values=True)))

    return urlunparse((scheme, netloc, path, "", query, ""))


def url_key(canonical_url: str) -> str:
    return "url-sha256:" + hashlib.sha256(
        canonical_url.encode("utf-8")
    ).hexdigest()


@app.post("/job")
async def queue_archive(req: ArchiveRequest, background_tasks: BackgroundTasks):
    # Normalize URL string
    # req.url = normalize_url(req.url)
    logging.info(req)
    id = jobs.create_job({
                            "status":   "queued",
                            "message":  "",
                            "url":      req.url, 
                            "url_hash": url_key(req.url),
                            "domain":   urlparse(req.url).netloc,
                            "depth":    req.depth,
                            "assets":   req.assets
                        })
    job = jobs.get_job(id)
    crawler_data = json.dumps(job) 
    logging.info(crawler_data)
    
    try:
    
        logging.info(crawler_data)
        jobs.update_job(id,{"status":"started"})

        crawl = crawler(id)
        background_tasks.add_task(run_crawl, crawl)
        
        jobs.update_job(id,{"status":"complete"})
    
    except subprocess.SubprocessError as e:

        logging.error(f"Subprocess failed: {e}")
        jobs.update_job(id,{"status":"failed"})
    
    return job


@app.get("/job/{id}")
def get_job(id: str):
    job = jobs.get_job(id)
    # if id not in jobs:
    #     raise HTTPException(404, "Job not found")
    return job


@app.get("/jobs")
def get_jobs():
    return jobs.list_jobs()


async def run_crawl(crawl):
    await crawl.run()

