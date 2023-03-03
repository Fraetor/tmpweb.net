#! /bin/bash
set -euo pipefail

# This file should be added to the crontab to be run daily.

curl -X DELETE http://127.0.0.1:8000
