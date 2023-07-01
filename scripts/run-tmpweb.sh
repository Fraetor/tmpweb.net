#! /bin/bash
set -euo pipefail

# This file should be added to the crontab to be run on reboot.

cd src/
screen -dmS tmpweb gunicorn tmpweb:app
