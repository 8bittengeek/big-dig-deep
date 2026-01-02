from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid, subprocess, os

app = FastAPI()
jobs = {}

class ArchiveRequest(BaseModel):
    url: str

@app.post("/archive")
def queue_archive(req: ArchiveRequest):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "url": req.url}
    subprocess.Popen(["python", "../crawler/crawler.py", req.url])
    jobs[job_id]["status"] = "started"
    return {"job_id": job_id, "status": "started"}

@app.get("/archive/{job_id}")
def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]
