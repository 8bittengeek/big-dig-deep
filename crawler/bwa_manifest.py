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
import sys
import datetime
import logging
import hashlib
import base64
import zipfile
import requests
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
    QDN_SERVICE = "WEBSITE_ARCHIVE"
    QDN_NAME = "big-web-archive"
    QDN_API_BASE = "http://localhost:8000" 

    def __init__(self, job_id, url_key, basedir = "jobs/manifest"):
        self.job_id = job_id
        self.url_key = url_key
        self.basedir = os.path.join(basedir, f"{job_id}.d")
        self.jobs = job_queue()
        self.job = self.jobs.get_job(self.job_id)
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


    @staticmethod
    def get_iso_timestamp():
        """
        Returns the current datetime in ISO 8601 format with UTC timezone.
        
        :returns: str: Datetime string in the format "2026-01-07T03:14:15Z"
        """
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def normalize_url(url):
        # examples only
        url = url.rstrip("/")
        url = url.lower()
        return url

    def content_hash(self):
        """Compute SHA256 hash of the WARC file."""
        warc_path = os.path.join(self.basedir, "warc", "crawl.warc.gz")
        if not os.path.exists(warc_path):
            return None
        with open(warc_path, "rb") as f:
            return "sha256:" + hashlib.sha256(f.read()).hexdigest()

    def get_previous_hash_from_qdn(self):
        """Query QDN for existing resource and return its content hash."""
        url = f"{self.QDN_API_BASE}/arbitrary/resources"
        params = {
            "service": self.QDN_SERVICE,
            "name": self.QDN_NAME,
            "identifier": self.url_key
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                resources = response.json()
                if resources:
                    # Assume the first resource is the latest; fetch its data to compute hash
                    resource = resources[0]
                    data_url = f"{self.QDN_API_BASE}/arbitrary/{resource['service']}/{resource['name']}/{resource['identifier']}"
                    data_response = requests.get(data_url)
                    if data_response.status_code == 200:
                        return "sha256:" + hashlib.sha256(data_response.content).hexdigest()
        except Exception as e:
            self.logger.error(f"Error querying QDN: {e}")
        return None

    def publish(self):
        # Compute current content hash
        current_hash = self.content_hash()
        if not current_hash:
            self.logger.error("WARC file not found, cannot publish")
            return None

        # Get previous hash from QDN
        previous_hash = self.get_previous_hash_from_qdn()

        # Compare hashes
        if previous_hash == current_hash:
            self.logger.info("Content unchanged, skipping QDN publish")
            return None

        # Content changed or new, proceed to publish
        manifest = {
            "schema": "big-web-archive/v1",
            "target_url": self.job["url"],
            "domain": self.job["domain"],
            "crawl_depth": self.job.get("depth", 2),
            "timestamp": self.get_iso_timestamp(),
            "content_hash": current_hash,
            "previous_hash": previous_hash,
            "warc": "warc/crawl.warc.gz",
            "artifacts": {
                "log": "metadata/crawl.log",
                "html": "metadata/snapshot.html",
                "png": "metadata/snapshot.png"
            }
        }

        # Create ZIP bundle
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add manifest JSON
            zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))
            # Add files
            files_to_add = [
                ("warc/crawl.warc.gz", "warc/crawl.warc.gz"),
                ("metadata/crawl.log", "metadata/crawl.log"),
                ("metadata/snapshot.html", "metadata/snapshot.html"),
                ("metadata/snapshot.png", "metadata/snapshot.png")
            ]
            for src, dst in files_to_add:
                src_path = os.path.join(self.basedir, src)
                if os.path.exists(src_path):
                    zip_file.write(src_path, dst)

        # Base64 encode the ZIP
        zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')

        # Publish to QDN
        publish_url = f"{self.QDN_API_BASE}/arbitrary/{self.QDN_SERVICE}/{self.QDN_NAME}/{self.url_key}/zip"
        data = {"data": zip_base64}
        try:
            response = requests.post(publish_url, json=data)
            if response.status_code == 200:
                self.logger.info("Successfully published to QDN")
                return manifest
            else:
                self.logger.error(f"Failed to publish to QDN: {response.status_code} {response.text}")
        except Exception as e:
            self.logger.error(f"Error publishing to QDN: {e}")

        return None


