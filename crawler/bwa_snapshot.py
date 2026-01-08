
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
import json
from pathlib import Path
import logging

class bwa_snapshot:
    def __init__(self, job, dirpath):
        self.job = job
        self.dirpath = dirpath

    def mkdir(self, dirpath):
        """
        Create a directory path if it does not exist.

        :dirpath: The path to the directory to be created.
        
        :returns: The path to the directory.
        """
        path = Path(dirpath)
        try:
            path.mkdir(parents=True, exist_ok=True)
        finally:
            logging.error("mkdir" + dirpath + "failed.")
        return path

    def mk_filepath(self, folder, filename):
            metadata_dirpath = os.path.join(self.dirpath, folder)
            self.mkdir(metadata_dirpath)
            metadata_filepath = os.path.join(metadata_dirpath, filename)
            return metadata_filepath

    async def warc(self, warc):
        try:
            warc_filepath = self.mk_filepath("warc","crawl.warc.gz")
            with open(warc_filepath, "wb") as f:
                f.write(warc.getvalue())
        finally:
            logging.error("warc file generation failed.")

    async def html(self, page):
        try:
            html_filepath = self.mk_filepath("metadata","snapshot.html")
            html = await page.content()
            with open(html_filepath, "w") as f:
                f.write(html)
        finally:
            logging.error("html file generation failed.")

    async def image(self, page):
        try:
            png_filepath = self.mk_filepath("metadata","snapshot.png")
            await page.screenshot(path=png_filepath, full_page=True)
        finally:
            logging.error("html file generation failed.")

    def job(self):
        try:
            log_filepath = self.mk_filepath("metadata","job.json")
            with open(log_filepath, "w") as f:
                f.write(json.dumps(self.job))
        finally:
            logging.error("job file generation failed.")

