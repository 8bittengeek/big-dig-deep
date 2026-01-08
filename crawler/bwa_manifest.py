
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
from datetime import datetime, timezone

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
    def __init__(self, job):
        self.job = job


    def get_iso_timestamp():
        """
        Returns the current datetime in ISO 8601 format with UTC timezone.
        
        :returns: str: Datetime string in the format "2026-01-07T03:14:15Z"
        """
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
        manifest["target_url"]      = self.job["url"]
        manifest["domain"]          = self.job["domain"]
        manifest["crawl_depth"]     = self.job["depth"]
        manifest["timestamp"]       = self.get_iso_timestamp()
        manifest["content_hash"]    = "sha256:abcd1234..."
        manifest["previous_hash"]   = "sha256:prev5678..."
        return manifest
    

