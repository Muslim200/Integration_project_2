#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y python3-pip python3.12-venv

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete. Activate with: source .venv/bin/activate"

