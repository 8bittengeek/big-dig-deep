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

    def list_jobs(self) -> list[dict[str, Any]]:
        """Return the contents of every job file in the jobs directory."""
        jobs = []
        for fname in os.listdir(self.jobs_dir):
            job_path = os.path.join(self.jobs_dir, fname)
            if os.path.isfile(job_path):
                with open(job_path, "rb") as f:
                    jobs.append(pickle.load(f))
        return jobs

    def count_jobs(self) -> int:
        """Return the number of job files stored in the jobs directory."""
        return len([name for name in os.listdir(self.jobs_dir)
                    if os.path.isfile(os.path.join(self.jobs_dir, name))])

    def remove_job(self, job_id: str) -> bool:
        """Remove a job file by UUID key. Returns True if removed, False if not found."""
        job_path = os.path.join(self.jobs_dir, job_id)
        if os.path.isfile(job_path):
            os.remove(job_path)
            return True
        return False
    
    def update_job(self, job_id: str, new_data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Update a job dict with new data and save it.
        Returns the updated job dict or None if job not found.
        """
        job = self.get_job(job_id)
        if job is None:
            return None

        # Merge new_data into existing job
        job.update(new_data)

        # Overwrite file
        job_path = os.path.join(self.jobs_dir, job_id)
        with open(job_path, "wb") as f:
            pickle.dump(job, f)

        return job