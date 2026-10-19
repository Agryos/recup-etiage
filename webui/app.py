"""
Application FastAPI de la WebUI.

Points d'entrée :
- ``GET /`` : sert l'interface web (HTML/CSS/JS).
- ``/api/types`` : schéma du formulaire (types de génération + champs).
- ``/api/jobs`` : création / liste / statut / annulation de jobs.
- ``/api/jobs/{id}/events`` : flux SSE des logs d'un job en temps réel.
- ``/api/output`` : navigation et téléchargement des fichiers générés.

Lancement (depuis la racine du projet, dans le venv) :
    python -m webui.app
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config.paths import OUTPUT_DIR, ROOT_DIR

from .job_manager import job_manager
from .schema import build_commands, build_types_schema

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Recup-Etiage WebUI", version="1.0")

# CORS permissif : permet d'appeler l'API depuis d'autres outils si besoin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class JobRequest(BaseModel):
    type: str
    params: dict


# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------

@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


# ----------------------------------------------------------------------------
# Métadonnées
# ----------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/types")
async def get_types():
    return build_types_schema()


# ----------------------------------------------------------------------------
# Jobs
# ----------------------------------------------------------------------------

@app.post("/api/jobs")
async def create_job(req: JobRequest):
    schema = build_types_schema()
    if req.type not in schema:
        raise HTTPException(status_code=400, detail=f"Type inconnu : {req.type}")
    try:
        commands = build_commands(req.type, req.params)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Paramètres invalides : {exc}")
    label = schema[req.type]["label"]
    job = job_manager.create_job(commands, label)
    return job.to_dict()


@app.get("/api/jobs")
async def list_jobs():
    return [job.to_dict() for job in job_manager.list_jobs()]


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    return job.to_dict()


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    if not job_manager.cancel_job(job_id):
        raise HTTPException(status_code=400, detail="Job non annulable (déjà terminé ?)")
    return job.to_dict()


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str):
    """Flux SSE : diffuse les logs d'un job en temps réel."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")

    async def event_stream():
        cursor = 0
        last_status = None
        while True:
            new_logs = job.get_logs_since(cursor)
            if new_logs:
                for line in new_logs:
                    cursor += 1
                    payload = json.dumps({"type": "log", "line": line}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
            if job.status != last_status:
                last_status = job.status
                payload = json.dumps(
                    {"type": "status", "status": job.status, "exit_code": job.exit_code},
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n"
            if job.status in ("completed", "failed", "cancelled"):
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ----------------------------------------------------------------------------
# Fichiers de sortie
# ----------------------------------------------------------------------------

def _safe_output_path(relative: str) -> Path:
    base = OUTPUT_DIR.resolve()
    target = (base / (relative or "")).resolve()
    if not target.is_relative_to(base):
        raise HTTPException(status_code=403, detail="Chemin non autorisé")
    return target


@app.get("/api/output")
async def list_output(path: str = ""):
    target = _safe_output_path(path)
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    items = []
    for entry in sorted(target.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
        items.append({
            "name": entry.name,
            "type": "dir" if entry.is_dir() else "file",
            "size": entry.stat().st_size if entry.is_file() else None,
        })
    return {"path": path, "items": items}


@app.get("/api/output/file")
async def serve_output_file(path: str):
    target = _safe_output_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(target, filename=target.name)


# ----------------------------------------------------------------------------
# Point d'entrée
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("WEBUI_HOST", "127.0.0.1")
    port = int(os.environ.get("WEBUI_PORT", "8000"))
    uvicorn.run("webui.app:app", host=host, port=port, reload=False)
