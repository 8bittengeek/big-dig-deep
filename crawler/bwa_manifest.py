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
import logging
from datetime import datetime, timezone
from .bwa_jobqueue import job_queue
# {
#   "schema": "big-web-archive/v1",
#   "target_url": "https://example.com",
#   "domain": "example.com",
#   "crawl_depth": 2,
#   "timestamp": "2026-01-07T03:14:15Z",
#   "content_hash": "sha256:abcd1234...",
#   "previous_hash": "sha256:prev5678...",
#   "warc": "warc/crawl.warc.gz",
#   "artifacts": {
#     "log": "metadata/crawl.log",
#     "html": "metadata/snapshot.html",
#     "png": "metadata/snapshot.png"
#   }
# }

class bwa_manifest:
    def __init__(self, job_id, basedir = "jobs/manifest"):
        self.job_id = job_id
        self.jobs = job_queue()
        self.job = self.jobs.get_job(self.job_id)
        self.dirpath = dirpath
        logging.basicConfig(
            level=logging.INFO,
            stream=sys.stdout,
            format="%(asctime)s %(levelname)s %(message)s"
        )

        # configure root logger *first*
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)]
        )

        # ensure Uvicorn loggers propagate
        for name in ("uvicorn.error", "uvicorn.access"):
            uv_logger = logging.getLogger(name)
            uv_logger.handlers.clear()
            uv_logger.propagate = True

        self.logger = logging.getLogger("bwa_snapshot")
        self.logger.setLevel(logging.DEBUG)


    def get_iso_timestamp():
        """
        Returns the current datetime in ISO 8601 format with UTC timezone.
        
        :returns: str: Datetime string in the format "2026-01-07T03:14:15Z"
        """
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def normalize_url(url):
        # examples only
        url = url.rstrip("/")
        url = url.lower()
        return url

    def content_hash(self):
        hash = "sha256:abcd1234..."
        return hash 
    
    def previous_hash(self):
        hash = "sha256:prev5678..."
        return hash

    def publish(self):
        manifest = {
                        "schema": "big-web-archive/v1",
                        "target_url": "https://example.com",
                        "domain": "example.com",
                        "crawl_depth": 2,
                        "timestamp": "2026-01-07T03:14:15Z",
                        "content_hash": "sha256:abcd1234...",
                        "previous_hash": "sha256:prev5678...",
                        "warc": "warc/crawl.warc.gz",
                        "artifacts": {
                            "log": "metadata/crawl.log",
                            "html": "metadata/snapshot.html",
                            "png": "metadata/snapshot.png"
                        }
                    }
        manifest["schema"]          = "big-web-archive/v1"
        manifest["target_url"]      = self.job["url"]
        manifest["domain"]          = self.job["domain"]
        manifest["crawl_depth"]     = self.job["depth"]
        manifest["timestamp"]       = self.get_iso_timestamp()
        manifest["content_hash"]    = "sha256:abcd1234..."
        manifest["previous_hash"]   = "sha256:prev5678..."
        manifest["warc"]            = "warc/crawl.warc.gz"
        manifest["artifacts"]       = {
                                        "log": "metadata/crawl.log",
                                        "html": "metadata/snapshot.html",
                                        "png": "metadata/snapshot.png"
                                    }
        return manifest


