"""
Unit tests for webui/job_manager.py — cycle de vie d'un job.

On utilise des commandes triviales (``python -c ...``) pour vérifier le cycle de
vie (création, exécution, statut, annulation) sans lancer de génération réelle.
"""
import sys
import time
from pathlib import Path

import pytest

# Ajoute la racine du projet au path (pour le paquet webui).
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.job_manager import Job, JobManager


def wait_for_terminal(job, timeout=10.0):
    """Attend que le job atteigne un état terminal (completed/failed/cancelled)."""
    deadline = time.time() + timeout
    while job.status in ("pending", "running") and time.time() < deadline:
        time.sleep(0.05)
    return job.status


class TestJob:
    """Objet Job : état initial, logs, sérialisation."""

    def test_etat_initial(self):
        job = Job("abc", [["echo", "hi"]], "test")
        assert job.status == "pending"
        assert job.logs == []
        assert job.exit_code is None

    def test_append_log_et_get_logs_since(self):
        job = Job("abc", [["echo", "hi"]], "test")
        job.append_log("ligne1\n")
        job.append_log("ligne2\n")
        assert job.get_logs_since(0) == ["ligne1\n", "ligne2\n"]
        assert job.get_logs_since(1) == ["ligne2\n"]

    def test_to_dict(self):
        job = Job("abc", [["python", "main.py", "--type", "hydraulicite"]], "Hydraulicite")
        d = job.to_dict()
        assert d["id"] == "abc"
        assert d["status"] == "pending"
        assert d["commands"] == ["python main.py --type hydraulicite"]
        assert d["log_count"] == 0


class TestJobManager:
    """JobManager : création, suivi, annulation."""

    def test_create_job_completes(self):
        mgr = JobManager()
        job = mgr.create_job([[sys.executable, "-c", "print('ok')"]], "ok")
        status = wait_for_terminal(job)
        assert status == "completed"
        assert job.exit_code == 0
        assert any("ok" in line for line in job.logs)

    def test_create_job_fails(self):
        mgr = JobManager()
        job = mgr.create_job([[sys.executable, "-c", "import sys; sys.exit(3)"]], "fail")
        status = wait_for_terminal(job)
        assert status == "failed"
        assert job.exit_code == 3

    def test_list_and_get(self):
        mgr = JobManager()
        job = mgr.create_job([[sys.executable, "-c", "pass"]], "x")
        wait_for_terminal(job)
        assert mgr.get_job(job.id) is job
        ids = [j.id for j in mgr.list_jobs()]
        assert job.id in ids

    def test_cancel_job_non_running(self):
        mgr = JobManager()
        job = mgr.create_job([[sys.executable, "-c", "pass"]], "x")
        wait_for_terminal(job)
        # Job déjà terminé => non annulable.
        assert mgr.cancel_job(job.id) is False

    def test_cancel_job_running(self):
        mgr = JobManager()
        # Commande longue pour pouvoir l'annuler pendant l'exécution.
        job = mgr.create_job([[sys.executable, "-c", "import time; time.sleep(30)"]], "long")
        # Attend que le job soit en cours ET que son processus soit créé :
        # sinon cancel_job renvoie False (le processus n'existe pas encore).
        deadline = time.time() + 5
        while (job.status != "running" or job.process is None) and time.time() < deadline:
            time.sleep(0.05)
        assert job.status == "running" and job.process is not None
        assert mgr.cancel_job(job.id) is True
        # Le processus a bien été terminé par l'annulation.
        assert job.process.poll() is not None
