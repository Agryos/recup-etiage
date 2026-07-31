#!/bin/bash

set -o allexport
source .env
set +o allexport

./venv/Scripts/pip.exe install -r ./requirements.txt
