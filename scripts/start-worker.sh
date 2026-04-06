#!/bin/sh
set -e
# Start Worker
export PYTHONPATH=$PYTHONPATH:/app
exec python -m worker.worker
