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
import asyncio
import logging
from pathlib import Path
import io
import aiofiles

class snapshot:
    def __init__(self, job, dirpath):
        self.job = job
        self.dirpath = dirpath
        self.logger = logging.getLogger(__name__)

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
            self.logger.error(f"Failed to create directory {dirpath}: {e}")
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

    async def warc(self, warc_buffer):
        """
        Generate WARC file from buffer.

        :param warc_buffer: Buffer containing WARC data
        """
        try:
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
            
            self.logger.info(f"WARC file generated: {warc_filepath}")
        except Exception as e:
            self.logger.error(f"WARC file generation failed: {e}")
            raise

    async def html(self, page):
        """
        Capture HTML content from page.

        :param page: Playwright page object
        """
        try:
            html_filepath = self.mk_filepath("metadata", "snapshot.html")
            html = await page.content()
            
            async with aiofiles.open(html_filepath, "w") as f:
                await f.write(html)
            
            self.logger.info(f"HTML snapshot saved: {html_filepath}")
        except Exception as e:
            self.logger.error(f"HTML file generation failed: {e}")
            raise

    async def image(self, page):
        """
        Capture full-page screenshot.

        :param page: Playwright page object
        """
        try:
            png_filepath = self.mk_filepath("metadata", "snapshot.png")
            await page.screenshot(path=png_filepath, full_page=True)
            
            self.logger.info(f"Screenshot saved: {png_filepath}")
        except Exception as e:
            self.logger.error(f"Screenshot generation failed: {e}")
            raise

    def job(self):
        """
        Save job metadata to JSON file.
        """
        try:
            log_filepath = self.mk_filepath("metadata", "job.json")
            with open(log_filepath, "w") as f:
                json.dump(self.job, f, indent=2)
            
            self.logger.info(f"Job metadata saved: {log_filepath}")
        except Exception as e:
            self.logger.error(f"Job file generation failed: {e}")
            raise