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
    QDN_API_BASE = "http://localhost:62392"  # Qortal QDN API base 

    def __init__(self, job_id, basedir = "jobs/manifest"):
        """
        Initialize the bwa_manifest instance.

        Purpose: Sets up the manifest handler for a specific job, including logging configuration and job queue access.

        Inputs:
        - job_id (str): The unique identifier for the job.
        - basedir (str, optional): Base directory for manifests, defaults to "jobs/manifest".

        Outputs: None

        Means: Initializes instance variables, configures logging for the application and Uvicorn, retrieves the job from the queue, and sets up a logger for the snapshot process.
        """
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
        """
        Set the job to a fault state and log the error message.

        Purpose: Marks the job as faulty and records the error for tracking.

        Inputs:
        - state (str): The fault state identifier.
        - msg (str): The error message to log and store.

        Outputs: None

        Means: Updates the job dictionary with fault status and message, persists the update to the job queue, and logs the error.
        """
        self.job["fault"] = state
        self.job["message"] = msg
        self.jobs.update_job(self.job_id,self.job)
        self.logger.error(msg)


    def status(self, state,  msg):
        """
        Update the job status and log the informational message.

        Purpose: Records the current status of the job for monitoring.

        Inputs:
        - state (str): The status state identifier.
        - msg (str): The informational message to log and store.

        Outputs: None

        Means: Updates the job dictionary with status and message, persists the update to the job queue, and logs the info.
        """
        self.job["status"] = state
        self.job["message"] = msg
        self.jobs.update_job(self.job_id,self.job)
        self.logger.info(msg)

    @staticmethod
    def get_iso_timestamp():
        """
        Returns the current datetime in ISO 8601 format with UTC timezone.

        Purpose: Provides a standardized timestamp for manifest metadata.

        Inputs: None

        Outputs: str: Datetime string in the format "2026-01-07T03:14:15Z"

        Means: Retrieves the current UTC time and formats it according to ISO 8601.
        """
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def normalize_url(url):
        """
        Normalize a URL for consistent keying.

        Purpose: Standardizes URLs to ensure consistent identification across jobs.

        Inputs:
        - url (str): The URL to normalize.

        Outputs: str: The normalized URL.

        Means: Strips trailing slashes and converts to lowercase.
        """
        # examples only
        url = url.rstrip("/")
        url = url.lower()
        return url

    def content_hash(self):
        """
        Compute SHA256 hash of the WARC file.

        Purpose: Generates a unique hash for the crawled content to detect changes.

        Inputs: None

        Outputs: str or None: The SHA256 hash prefixed with "sha256:", or None if the WARC file is missing.

        Means: Reads the WARC file from the job's basedir and computes its SHA256 hash.
        """
        warc_path = os.path.join(self.basedir, "warc", "crawl.warc.gz")
        if not os.path.exists(warc_path):
            return None
        with open(warc_path, "rb") as f:
            return "sha256:" + hashlib.sha256(f.read()).hexdigest()

    def get_previous_hash_from_qdn(self, url_key):
        """
        Query QDN for existing resources, find the latest for this url_key, and return its content hash.

        Purpose: Retrieves the most recent content hash from QDN to compare for changes.

        Inputs:
        - url_key (str): The normalized URL key to search for.

        Outputs: str or None: The content hash of the latest manifest, or None if no manifests exist.

        Means: Fetches all manifests for the url_key, identifies the head of the hash chain (no previous_hash), and returns its content_hash.
        """
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
        """
        Publish the manifest and ZIP bundle to QDN if content has changed.

        Purpose: Stores the web archive on QDN with versioning based on content hash.

        Inputs:
        - url_key (str): The normalized URL key for the archive.

        Outputs: dict or None: The published manifest if successful, or None if unchanged or failed.

        Means: Computes content hash, compares with previous, creates ZIP bundle with manifest and files, publishes to QDN, and cleans up source directory.
        """
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
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            try:
                response = requests.post(publish_url, json=data, headers=headers, timeout=10)  # 10 second timeout
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
        """
        Get all manifests for a given url_key from QDN.

        Purpose: Retrieves all archived versions for a URL from the decentralized network.

        Inputs:
        - url_key (str): The normalized URL key to search for.

        Outputs: list: List of tuples (identifier, manifest_dict, zip_bytes) for matching resources.

        Means: Queries QDN resources, downloads and parses ZIP files to extract manifests matching the url_key.
        """
        url = f"{self.QDN_API_BASE}/arbitrary"  # Remove /resources
        params = {
            "service": self.QDN_SERVICE,
            "name": self.QDN_NAME
        }
        manifests = []
        try:
            response = requests.get(url, params=params, timeout=10)  # 10 second timeout
            if response.status_code == 200:
                resources = response.json()
                self.logger.info(f"Successfully retrieved {len(resources)} resources from QDN")
                for resource in resources:
                    data_url = f"{self.QDN_API_BASE}/arbitrary/{resource['service']}/{resource['name']}/{resource['identifier']}"
                    headers = {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    data_response = requests.get(data_url, timeout=10, headers=headers)  # 10 second timeout
                    if data_response.status_code == 200:
                        zip_data = io.BytesIO(data_response.content)
                        with zipfile.ZipFile(zip_data, 'r') as zip_file:
                            if 'manifest.json' in zip_file.namelist():
                                manifest_data = zip_file.read('manifest.json')
                                manifest = json.loads(manifest_data.decode('utf-8'))
                                if manifest.get('url_key') == url_key:
                                    manifests.append((resource['identifier'], manifest, zip_data.getvalue()))
                    else:
                        self.logger.error(f"Failed to download resource: {data_response.status_code} {data_response.text}")
            else:
                self.logger.error(f"Failed to get resources: {response.status_code} {response.text}")
        except Exception as e:
            self.logger.error(f"Error getting manifests: {e}")
        return manifests

    def get_most_recent_zip(self, url_key):
        """
        Retrieve the most recent archive ZIP file for the given url_key and save it to disk.

        Purpose: Downloads the latest version of the web archive for viewing or processing.

        Inputs:
        - url_key (str): The normalized URL key.

        Outputs: str or None: The content hash of the saved ZIP, or None if no manifests found.

        Means: Identifies the head of the hash chain, saves the corresponding ZIP to jobs/manifest/dl/{job_id}/{url_key}/{content_hash}.zip.
        """
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
        """
        Retrieve a list of all ZIP files for the url_key, sorted by content_hash link order, and save them to disk.

        Purpose: Downloads the entire version history of the web archive in chronological order.

        Inputs:
        - url_key (str): The normalized URL key.

        Outputs: list: List of content hashes for the saved ZIPs.

        Means: Builds the hash chain from head to tail, saves each ZIP to jobs/manifest/dl/{job_id}/{url_key}/{content_hash}.zip in order.
        """
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

    def extract_zip(self, url_key, content_hash):
        """
        Extract the ZIP file for the given url_key and content_hash, and return the path to the extracted directory.

        Purpose: Unpacks the archive for GUI viewing or further processing.

        Inputs:
        - url_key (str): The normalized URL key.
        - content_hash (str): The content hash of the ZIP to extract.

        Outputs: str or None: Path to the extracted directory, or None if extraction fails.

        Means: Extracts the ZIP to jobs/manifest/dl/{job_id}/{url_key}/{content_hash}/ and returns the path.
        """
        zip_path = os.path.join("jobs", "manifest", "dl", self.job_id, url_key, f"{content_hash}.zip")
        extract_dir = os.path.join("jobs", "manifest", "dl", self.job_id, url_key, content_hash)
        
        if not os.path.exists(zip_path):
            self.logger.error(f"ZIP file not found: {zip_path}")
            return None
        
        try:
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            self.logger.info(f"Extracted ZIP to {extract_dir}")
            return extract_dir
        except Exception as e:
            self.logger.error(f"Failed to extract ZIP {zip_path}: {e}")
            return None

    def cleanup(self):
        """
        Clean up all downloaded and extracted files for this job_id.

        Purpose: Removes temporary files to free disk space without affecting shared resources.

        Inputs: None

        Outputs: None

        Means: Deletes the jobs/manifest/dl/{job_id} directory and its contents.
        """
        dl_dir = os.path.join("jobs", "manifest", "dl", self.job_id)
        try:
            if os.path.exists(dl_dir):
                shutil.rmtree(dl_dir)
                self.logger.info(f"Cleaned up directory: {dl_dir}")
            else:
                self.logger.info(f"No directory to clean: {dl_dir}")
        except Exception as e:
            self.logger.error(f"Failed to clean up {dl_dir}: {e}")


