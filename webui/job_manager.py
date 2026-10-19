"""
Gestionnaire de jobs pour la WebUI.

Chaque job exécute une ou plusieurs commandes (typiquement ``python main.py ...``)
en sous-processus, capture la sortie (stdout + stderr) en temps réel et la conserve
en mémoire pour diffusion aux clients via SSE (Server-Sent Events).

Le choix du sous-processus (plutôt qu'un appel direct de ``main()``) garantit :
- une isolation complète : un plantage d'un job ne fait pas tomber le serveur ;
- une annulation simple (on tue le processus) ;
- un comportement strictement identique au mode CLI.
"""

import subprocess
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from src.config.paths import ROOT_DIR


class Job:
    """Représente une tâche de génération lancée depuis la WebUI."""

    def __init__(self, job_id: str, commands: List[List[str]], label: str):
        self.id = job_id
        self.commands = commands
        self.label = label
        self.status = "pending"  # pending | running | completed | failed | cancelled
        self.logs: List[str] = []
        self._lock = threading.Lock()
        self.process: Optional[subprocess.Popen] = None
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.exit_code: Optional[int] = None
        self.current_command_index = 0

    def append_log(self, line: str) -> None:
        with self._lock:
            self.logs.append(line)

    def get_logs_since(self, index: int) -> List[str]:
        with self._lock:
            return self.logs[index:]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "exit_code": self.exit_code,
            "commands": [" ".join(c) for c in self.commands],
            "log_count": len(self.logs),
        }


class JobManager:
    """Crée, suit et annule des jobs de génération."""

    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create_job(self, commands: List[List[str]], label: str) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(job_id, commands, label)
        with self._lock:
            self.jobs[job_id] = job
        thread = threading.Thread(target=self._run_job, args=(job,), daemon=True)
        thread.start()
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self.jobs.get(job_id)

    def list_jobs(self) -> List[Job]:
        with self._lock:
            jobs = list(self.jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if not job or job.status != "running":
            return False
        if job.process and job.process.poll() is None:
            job.process.terminate()
            try:
                job.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                job.process.kill()
            job.status = "cancelled"
            job.finished_at = datetime.now()
            job.append_log("\n[Job annulé par l'utilisateur]\n")
            return True
        return False

    def _run_job(self, job: Job) -> None:
        job.status = "running"
        job.started_at = datetime.now()
        job.append_log(f"=== Job {job.id} démarré ({job.label}) ===\n")
        try:
            for i, cmd in enumerate(job.commands):
                job.current_command_index = i
                job.append_log(f"\n$ {' '.join(cmd)}\n")
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(ROOT_DIR),
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                job.process = process
                for line in process.stdout:
                    job.append_log(line)
                process.wait()
                job.exit_code = process.returncode
                job.append_log(f"[Commande terminée - code {process.returncode}]\n")
                if process.returncode != 0:
                    job.status = "failed"
                    break
            else:
                job.status = "completed"
        except Exception as exc:  # pragma: no cover - garde-fou
            job.status = "failed"
            job.append_log(f"\n[Erreur interne du gestionnaire : {exc}]\n")
        finally:
            job.finished_at = datetime.now()
            job.append_log(f"=== Job {job.id} terminé ({job.status}) ===\n")


# Instance unique partagée par l'application FastAPI.
job_manager = JobManager()
