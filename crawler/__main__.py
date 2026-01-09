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

import asyncio
import argparse
import json
import bwa_crawl

parser = argparse.ArgumentParser()
parser.add_argument('--data', type=json.loads)
args = parser.parse_args()

job = args.data
crawler = bwa_crawl.crawler(job,"bwa_warc")

async def run_job():
    job = await crawler.run()
    return job

if __name__ == "__main__":
    asyncio.run(run_job())
    print(json.dumps(job))
