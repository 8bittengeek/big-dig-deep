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

import uuid
import subprocess
import os
import logging
import json
import hashlib
import base64

app = FastAPI()
jobs = {}

class ArchiveRequest(BaseModel):
    url: str

def url_hash(url, salt=None):
    # Normalize URL string
    normalized_url = url.lower().strip()
    
    # Create base hash
    base_hash = hashlib.sha256(normalized_url.encode('utf-8')).digest()
    
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

@app.post("/archive")
def queue_archive(req: ArchiveRequest):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"job_id":   job_id, 
                    "status":   "queued", 
                    "url":      req.url, 
                    "url_hash": url_hash(req.url),
                    "domain":   urlparse(req.url).netloc}
    crawler_data = json.dumps(jobs[job_id]) 
    print(crawler_data)
    try:
        logging.info(crawler_data)
        subprocess.Popen(["python", "crawler/crawler.py", "--data", crawler_data])
        jobs[job_id]["status"] = "started"
    except subprocess.SubprocessError as e:
        logging.error(f"Subprocess failed: {e}")
        jobs[job_id]["status"] = "failed"
    return jobs[job_id]

@app.get("/archive/{job_id}")
def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]
