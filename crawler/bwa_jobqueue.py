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
    def __init__(self, jobs_dir: str = "jobs/queue"):
        self.jobs_dir = jobs_dir
        os.makedirs(self.jobs_dir, exist_ok=True)

    def _job_path(self, job_id: str) -> str:
        """Return the job filename with .job suffix."""
        return os.path.join(self.jobs_dir, f"{job_id}.job")

    def create_job(self, job_data: dict[str, Any]) -> str:
        """Create a new job, save to a .job file, return the UUID key."""
        job_id = uuid.uuid4().hex
        job_dict = {"id": job_id, **job_data}

        job_path = self._job_path(job_id)
        tmp_path = job_path + ".tmp"

        # Write to a temporary file first
        with open(tmp_path, "wb") as f:
            pickle.dump(job_dict, f)
            f.flush()
            os.fsync(f.fileno())

        # Atomically rename into place
        os.replace(tmp_path, job_path)
        return job_id

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Retrieve a saved job by its UUID key."""
        job_path = self._job_path(job_id)
        if not os.path.isfile(job_path):
            return None

        try:
            with open(job_path, "rb") as f:
                return pickle.load(f)
        except (EOFError, pickle.PickleError):
            # file exists but is empty or invalid
            return None

    def list_jobs(self) -> list[dict[str, Any]]:
        """Return the contents of every job file in the jobs directory."""
        jobs = []
        for fname in os.listdir(self.jobs_dir):
            # Only count .job files
            if not fname.endswith(".job"):
                continue

            job_path = os.path.join(self.jobs_dir, fname)
            if os.path.isfile(job_path):
                try:
                    with open(job_path, "rb") as f:
                        jobs.append(pickle.load(f))
                except (EOFError, pickle.PickleError):
                    # skip empty/invalid files
                    continue
        return jobs

    def count_jobs(self) -> int:
        """Return the number of job files stored."""
        return len([
            name for name in os.listdir(self.jobs_dir)
            if name.endswith(".job") and os.path.isfile(os.path.join(self.jobs_dir, name))
        ])

    def remove_job(self, job_id: str) -> bool:
        """Remove a job file by UUID key."""
        job_path = self._job_path(job_id)
        if os.path.isfile(job_Path):
            os.remove(job_path)
            return True
        return False

    def update_job(self, job_id: str, new_data: dict[str, Any]) -> dict[str, Any] | None:
        """Update an existing job .job file with new data."""
        job = self.get_job(job_id)
        if job is None:
            return None

        job.update(new_data)

        job_path = self._job_path(job_id)
        tmp_path = job_path + ".tmp"

        with open(tmp_path, "wb") as f:
            pickle.dump(job, f)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, job_path)
        return job
