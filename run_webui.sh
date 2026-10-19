#!/bin/bash
# Lance la WebUI de Recup-Etiage.
# Usage : ./run_webui.sh
#
# Prérequis : le venv doit être créé et les dépendances installées
# (voir install.sh + requirements-webui.txt).

set -e

# Chemin du projet (dossier du script).
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Charge le .env (proxy éventuel).
if [ -f .env ]; then
    set -o allexport
    source .env
    set +o allexport
fi

# Interpréteur Python : venv si présent, sinon python3.
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
elif [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

echo "Lancement de la WebUI sur http://127.0.0.1:8000 ..."
echo "Appuyez sur Ctrl+C pour arrêter."
"$PYTHON" -m webui.app
