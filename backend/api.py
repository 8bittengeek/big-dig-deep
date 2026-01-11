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
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from urllib.parse import urlparse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import BackgroundTasks
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from crawler.bwa_crawl import crawler
from crawler.bwa_jobqueue import job_queue
from crawler.bwa_manifest import bwa_manifest

import os
import subprocess
import logging
import json
import hashlib
from pathlib import Path


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs = job_queue()

class ArchiveRequest(BaseModel):
    op: str
    url: str = ""
    id: str = ""
    depth: int = 1
    assets: bool = False


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


async def get_archive_async(temp_job_id: str, url_key_val: str):
    """
    Asynchronously fetch archive from QDN and update job status.
    
    Args:
        temp_job_id: Temporary job ID for tracking
        url_key_val: URL key to fetch
    """
    try:
        # Create temporary job for tracking
        jobs.create_job({
            "id": temp_job_id,
            "status": "fetching",
            "message": "Downloading archive from QDN...",
            "url_key": url_key_val
        })
        
        # Fetch from QDN
        manifest = bwa_manifest(temp_job_id, "jobs/manifest")  # Correct basedir parameter
        content_hash = manifest.get_most_recent_zip(url_key_val)
        
        if content_hash:
            extract_dir = manifest.extract_zip(url_key_val, content_hash)
            # Update job with success
            jobs.update_job(temp_job_id, {
                "status": "complete",
                "message": f"Archive ready: {extract_dir}",
                "path": extract_dir,
                "content_hash": content_hash
            })
        else:
            # Update job with error
            jobs.update_job(temp_job_id, {
                "status": "failed",
                "message": "No archive found for this URL"
            })
            
    except Exception as e:
        # Update job with error
        jobs.update_job(temp_job_id, {
            "status": "failed", 
            "message": f"Error fetching archive: {str(e)}"
        })
        logging.error(f"Error in get_archive_async: {e}")


@app.post("/job")
async def queue_archive(req: ArchiveRequest, background_tasks: BackgroundTasks):
    if req.op == "new":
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
            background_tasks.add_task(run_crawl, crawl)  # Run in background
        
        except subprocess.SubprocessError as e:

            logging.error(f"Subprocess failed: {e}")
            jobs.update_job(id,{"status":"failed"})
        
        return job
    
    elif req.op == "get":
        # Get archived job (check local first, then QDN)
        url_key_val = url_key(req.url)
        
        # Check if archive already exists locally
        jobs_list = jobs.list_jobs()
        
        # Handle both list and dict return types
        if hasattr(jobs_list, 'items'):
            # It's a dictionary-like object
            jobs_dict = jobs_list
        else:
            # It's a list
            jobs_dict = {job_id: job_data for job_id, job_data in jobs_list}
        
        for job_id, job_data in jobs_dict.items():
            if job_data.get('url_key') == url_key_val and job_data.get('status') == 'complete':
                extract_dir = os.path.join("jobs", "manifest", job_id, "metadata")
                if os.path.exists(extract_dir):
                    return {"path": extract_dir, "content_hash": job_data.get('content_hash'), "local": True}
        
        # Use a temporary job id for manifest operations
        temp_job_id = f"get_{hash(url_key_val)}"  # simple hash
        
        # Run as background task to avoid blocking
        background_tasks.add_task(get_archive_async, temp_job_id, url_key_val)
        
        # Return immediate response with job ID for status tracking
        return {"status": "fetching", "job_id": temp_job_id, "url_key": url_key_val}
    
    elif req.op == "jobs":
        return jobs.list_jobs()
    
    elif req.op == "job":
        job = jobs.get_job(req.id)
        if not job:
            raise HTTPException(404, "Job not found")
        return job
    
    else:
        raise HTTPException(400, "Invalid operation")


@app.get("/archive-content")
async def serve_archive_content(path: str):
    """
    Serve archived HTML content for display in the Q-App viewer.
    """
    try:
        # Validate the path to prevent directory traversal
        file_path = Path(path).resolve()
        
        # Ensure the path is within allowed directories (jobs/extracted or similar)
        if not str(file_path).startswith("/app/jobs/") and not str(file_path).startswith("./jobs/"):
            raise HTTPException(403, "Access denied: Path outside allowed directory")
        
        if not file_path.exists():
            raise HTTPException(404, "File not found")
        
        if not file_path.is_file():
            raise HTTPException(400, "Path is not a file")
        
        # Read the file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        return PlainTextResponse(content, media_type="text/html")
        
    except Exception as e:
        logging.error(f"Error serving archive content: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


async def run_crawl(crawl):
    await crawl.run()

