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

import uuid
import subprocess
import logging
import json
import hashlib
import base64

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs = {}

class ArchiveRequest(BaseModel):
    url: str

def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        return "http://" + url
    return url

def url_hash(url, salt=None):
    # Create base hash
    base_hash = hashlib.sha256(url.encode('utf-8')).digest()
    # Add optional salt
    if salt:
        base_hash = hashlib.sha256(base_hash + salt.encode('utf-8')).digest()
    # Create multiple representations
    hex_hash = base_hash.hex()
    base64_hash = base64.urlsafe_b64encode(base_hash).decode('utf-8')
    return {
        'hex': hex_hash,
        'base64': base64_hash,
        'length': len(hex_hash)
    }

@app.post("/job")
def queue_archive(req: ArchiveRequest):
    # Normalize URL string
    req.url = normalize_url(req.url)
    id = str(uuid.uuid4())
    jobs[id] = {"id":   id, 
                    "status":   "queued", 
                    "url":      req.url, 
                    "url_hash": url_hash(req.url),
                    "domain":   urlparse(req.url).netloc}
    crawler_data = json.dumps(jobs[id]) 
    logging.info(crawler_data)
    try:
        logging.info(crawler_data)
        subprocess.Popen(["python", "crawler/crawler.py", "--data", crawler_data])
        jobs[id]["status"] = "started"
    except subprocess.SubprocessError as e:
        logging.error(f"Subprocess failed: {e}")
        jobs[id]["status"] = "failed"
    return jobs[id]

@app.get("/job/{id}")
def get_job(id: str):
    if id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[id]

@app.get("/jobs")
def get_jobs():
    return jobs

