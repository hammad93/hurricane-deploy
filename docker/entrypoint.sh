#!/bin/bash

# Start the run once job.
echo "Docker container has been started"

declare -p | grep -Ev 'BASHOPTS|BASH_VERSINFO|EUID|PPID|SHELLOPTS|UID' > /container.env

# run the tensorflow server
service hurricane start
service hurricane enable

# Setup a cron schedule
echo "SHELL=/bin/bash
BASH_ENV=/container.env
0 * * * * python /hurricane-deploy/report.py >> /var/log/cron.log 2>&1
# This extra line makes it a valid cron" > scheduler.txt

crontab scheduler.txt
cron -f