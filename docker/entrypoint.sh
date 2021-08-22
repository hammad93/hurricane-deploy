#!/bin/bash

# Start the run once job.
echo "Docker container has been started"

declare -p | grep -Ev 'BASHOPTS|BASH_VERSINFO|EUID|PPID|SHELLOPTS|UID' > /container.env

# run the tensorflow server
python /home/bitnami/hurricane-deploy/download_models.py
nohup tensorflow_model_server --model_base_path=/root/forecast --rest_api_port=9000 --model_name=hurricane &

# Setup a cron schedule
echo "SHELL=/bin/bash
BASH_ENV=/container.env
0 * * * * python /home/bitnami/hurricane-deploy/report.py >> /var/log/cron.log 2>&1
# This extra line makes it a valid cron" > scheduler.txt

crontab scheduler.txt
cron -f