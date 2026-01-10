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
import uuid
import pickle
from typing import Any

class job_queue:
    def __init__(self, jobs_dir: str = "../jobs"):
        self.jobs_dir = jobs_dir
        os.makedirs(self.jobs_dir, exist_ok=True)

    def create_job(self, job_data: dict[str, Any]) -> str:
        """Create a new job, save to file, return the UUID key."""
        job_id = uuid.uuid4().hex
        job_dict = {"id": job_id, **job_data}

        # Save to file
        job_path = os.path.join(self.jobs_dir, job_id)
        with open(job_path, "wb") as f:
            pickle.dump(job_dict, f)

        return job_id

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Retrieve a saved job by its UUID key."""
        job_path = os.path.join(self.jobs_dir, job_id)
        if not os.path.isfile(job_path):
            return None

        with open(job_path, "rb") as f:
            return pickle.load(f)

    def list_jobs(self) -> list[str]:
        """List all saved job UUID keys."""
        return os.listdir(self.jobs_dir)
