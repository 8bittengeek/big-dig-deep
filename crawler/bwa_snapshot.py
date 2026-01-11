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

import io
import os
import sys
import json
import asyncio
import logging
import aiofiles
from pathlib import Path
from .bwa_jobqueue import job_queue

class snapshot:

    def __init__(self, job_id, dirpath):
        self.job_id = job_id
        self.jobs = job_queue()
        self.job = self.jobs.get_job(self.job_id)
        self.dirpath = dirpath
        
        # configure logger for this instance only (don't configure globally)
        self.logger = logging.getLogger(f"bwa_snapshot.{job_id}")
        self.logger.setLevel(logging.DEBUG)
        
        # Only add handler if logger doesn't already have one
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s"
            ))
            self.logger.addHandler(handler)

        # ensure Uvicorn loggers propagate
        for name in ("uvicorn.error", "uvicorn.access"):
            uv_logger = logging.getLogger(name)
            uv_logger.handlers.clear()
            uv_logger.propagate = True


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


    def mkdir(self, dirpath):
        """
        Create a directory path if it does not exist.

        :param dirpath: The path to the directory to be created.
        :returns: The path to the directory.
        """
        path = Path(dirpath)
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError as e:
            self.fault("mkdir",f"Failed to create directory {dirpath}: {e}")
            raise


    def mk_filepath(self, folder, filename):
        """
        Create a filepath for a specific folder and filename.

        :param folder: Subfolder name
        :param filename: Filename
        :returns: Full filepath
        """
        metadata_dirpath = os.path.join(self.dirpath, folder)
        self.mkdir(metadata_dirpath)
        return os.path.join(metadata_dirpath, filename)


    async def store_warc(self, warc_buffer):
        """
        Generate WARC file from buffer.

        :param warc_buffer: Buffer containing WARC data
        """
        try:
            self.status("warc",f"WARC file generation started.")

            # Ensure warc_buffer is resolved
            if asyncio.iscoroutine(warc_buffer):
                buffer_content = await warc_buffer
            elif isinstance(warc_buffer, io.BytesIO):
                buffer_content = warc_buffer
            else:
                raise TypeError(f"Unexpected buffer type: {type(warc_buffer)}")

            warc_filepath = self.mk_filepath("warc", "crawl.warc.gz")
            
            async with aiofiles.open(warc_filepath, "wb") as f:
                await f.write(buffer_content.getvalue())
            
            self.status("warc",f"WARC file generated: {warc_filepath}")
        except Exception as e:
            self.fault("warc",f"WARC file generation failed: {e}")
            raise


    async def store_html(self, page):
        """
        Capture HTML content from page.

        :param page: Playwright page object
        """
        try:
            html_filepath = self.mk_filepath("metadata", "snapshot.html")
            html = await page.content()
            
            async with aiofiles.open(html_filepath, "w") as f:
                await f.write(html)
            
            self.status("html",f"HTML snapshot saved: {html_filepath}")
        except Exception as e:
            self.fault("html",f"HTML file generation failed: {e}")
            raise


    async def store_image(self, page):
        """
        Capture full-page screenshot.

        :param page: Playwright page object
        """
        try:
            png_filepath = self.mk_filepath("metadata", "snapshot.png")
            await page.screenshot(path=png_filepath, full_page=True)
            
            self.status("image",f"Screenshot saved: {png_filepath}")
        except Exception as e:
            self.fault("image",f"Screenshot generation failed: {e}")
            raise


    def store_job(self):
        """
        Save job metadata to JSON file.
        """
        try:
            log_filepath = self.mk_filepath("metadata", "job.json")
            with open(log_filepath, "w") as f:
                json.dump(self.job, f, indent=2)
            
            self.status("job",f"Job metadata saved: {log_filepath}")
        except Exception as e:
            self.fault("job",f"Job file generation failed: {e}")
            raise

    def get_job(self):
        return self.job;
