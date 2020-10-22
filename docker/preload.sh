#!/bin/bash

set -eo pipefail

/misc/prerun.sh &

python -u /misc/wait.py

echo "end"
