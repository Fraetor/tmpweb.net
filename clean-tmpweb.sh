#! /bin/bash
set -euo pipefail

# This file should be added to the crontab to be run daily.

cd src/
python3 -c 'import tmpweb; tmpweb.delete_old_sites()'
