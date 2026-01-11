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
import shutil
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

    def __init__(self, job_id, basedir = "jobs/manifest"):
        self.job_id = job_id
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


    def fault(self, state, msg):
        self.job["fault"] = state
        self.job["message"] = msg
        self.jobs.update_job(self.job_id,self.job)
        self.logger.error(msg)


    def status(self, state,  msg):
        self.job["status"] = state
        self.job["message"] = msg
        self.jobs.update_job(self.job_id,self.job)
        self.logger.info(msg)

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

    def get_previous_hash_from_qdn(self, url_key):
        """Query QDN for existing resources, find the latest for this url_key, and return its content hash."""
        manifests = self.get_manifests_for_url_key(url_key)
        if manifests:
            # Find the latest: the one with no previous_hash
            for ident, manifest, _ in manifests:
                if not manifest.get('previous_hash'):
                    return manifest.get('content_hash')
            # If none found, return the first one's content_hash
            return manifests[0][1].get('content_hash')
        return None

    def publish(self, url_key):
        # Compute current content hash
        current_hash = self.content_hash()
        if not current_hash:
            self.logger.error("WARC file not found, cannot publish")
            return None

        # Get previous hash from QDN
        previous_hash = self.get_previous_hash_from_qdn(url_key)

        # Compare hashes - only publish if the content hash has chnaged
        if previous_hash != current_hash:

            # Content changed or new, proceed to publish
            manifest = {
                "schema": "big-web-archive/v1",
                "url_key": url_key,
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
            identifier = current_hash.replace("sha256:", "")
            publish_url = f"{self.QDN_API_BASE}/arbitrary/{self.QDN_SERVICE}/{self.QDN_NAME}/{identifier}/zip"
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

        else:
            
            self.logger.info("Content unchanged, skipping QDN publish")
            return None

        # Cleanup: remove the source directory regardless of publish outcome
        try:
            if os.path.exists(self.basedir):
                shutil.rmtree(self.basedir)
                self.logger.info(f"Cleaned up source directory: {self.basedir}")
        except Exception as e:
            self.logger.error(f"Failed to clean up source directory {self.basedir}: {e}")

        return None

    def get_manifests_for_url_key(self, url_key):
        """Get all manifests for a given url_key from QDN."""
        url = f"{self.QDN_API_BASE}/arbitrary/resources"
        params = {
            "service": self.QDN_SERVICE,
            "name": self.QDN_NAME
        }
        manifests = []
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                resources = response.json()
                for resource in resources:
                    data_url = f"{self.QDN_API_BASE}/arbitrary/{resource['service']}/{resource['name']}/{resource['identifier']}"
                    data_response = requests.get(data_url)
                    if data_response.status_code == 200:
                        zip_data = io.BytesIO(data_response.content)
                        with zipfile.ZipFile(zip_data, 'r') as zip_file:
                            if 'manifest.json' in zip_file.namelist():
                                manifest_data = zip_file.read('manifest.json')
                                manifest = json.loads(manifest_data.decode('utf-8'))
                                if manifest.get('url_key') == url_key:
                                    manifests.append((resource['identifier'], manifest, zip_data.getvalue()))
        except Exception as e:
            self.logger.error(f"Error getting manifests: {e}")
        return manifests

    def get_most_recent_zip(self, url_key):
        """Retrieve the most recent archive ZIP file for the given url_key and save it to disk."""
        manifests = self.get_manifests_for_url_key(url_key)
        if not manifests:
            return None
        # Find the one with no previous_hash (the head of the chain)
        for ident, manifest, zip_bytes in manifests:
            if not manifest.get('previous_hash'):
                content_hash = manifest.get('content_hash', 'unknown').replace('sha256:', '')
                save_path = os.path.join("jobs", "manifest", "dl", self.job_id, url_key, f"{content_hash}.zip")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(zip_bytes)
                self.logger.info(f"Saved most recent ZIP to {save_path}")
                return content_hash
        # If none, save the first one
        if manifests:
            ident, manifest, zip_bytes = manifests[0]
            content_hash = manifest.get('content_hash', 'unknown').replace('sha256:', '')
            save_path = os.path.join("jobs", "manifest", "dl", self.job_id, url_key, f"{content_hash}.zip")
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(zip_bytes)
            self.logger.info(f"Saved most recent ZIP to {save_path}")
            return content_hash
        return None

    def get_all_zips_sorted(self, url_key):
        """Retrieve a list of all ZIP files for the url_key, sorted by content_hash link order, and save them to disk."""
        manifests = self.get_manifests_for_url_key(url_key)
        if not manifests:
            return []
        
        # Build the chain: start from the one with no previous_hash
        chain = {}
        for ident, manifest, zip_bytes in manifests:
            chash = manifest.get('content_hash')
            prev_hash = manifest.get('previous_hash')
            chain[chash] = (manifest, zip_bytes)
        
        # Find the head (no previous_hash)
        head = None
        for chash, (manifest, _) in chain.items():
            if not manifest.get('previous_hash'):
                head = chash
                break
        
        saved_hashes = []
        if not head:
            # If no head, save all
            for ident, manifest, zip_bytes in manifests:
                content_hash = manifest.get('content_hash', 'unknown').replace('sha256:', '')
                save_path = os.path.join("jobs", "manifest", "dl", self.job_id, url_key, f"{content_hash}.zip")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(zip_bytes)
                saved_hashes.append(content_hash)
        else:
            # Follow the chain
            current = head
            while current:
                if current in chain:
                    manifest, zip_bytes = chain[current]
                    content_hash = current.replace('sha256:', '')
                    save_path = os.path.join("jobs", "manifest", "dl", self.job_id, url_key, f"{content_hash}.zip")
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    with open(save_path, 'wb') as f:
                        f.write(zip_bytes)
                    saved_hashes.append(content_hash)
                    # Find next: the one whose previous_hash is current
                    next_chash = None
                    for chash, (m, _) in chain.items():
                        if m.get('previous_hash') == current:
                            next_chash = chash
                            break
                    current = next_chash
                else:
                    break
        
        self.logger.info(f"Saved {len(saved_hashes)} ZIPs to jobs/manifest/dl/{self.job_id}/{url_key}/")
        return saved_hashes


