FROM continuumio/anaconda3:2020.07

# Google Artificial Intelligence Platform Api Authentication

COPY authentication.json /root/
ENV GOOGLE_APPLICATION_CREDENTIALS=/root/authentication.json

# SMTP credentials

COPY credentials.csv /root/

# Python additional requirements

COPY requirements.txt /root/
RUN pip install -r /root/requirements.txt

# Add git repository

RUN git clone --single-branch --branch master https://github.com/hammad93/hurricane-deploy.git

# Setup cron job

RUN apt-get update && apt-get -y install cron
# Copy hello-cron file to the cron.d directory
COPY email-cron /root/email-cron
# Give execution rights on the cron job
RUN chmod 0644 /root/email-cron
# Apply cron job
RUN crontab /root/email-cron
# Create the log file to be able to run tail
RUN touch /root/cron.log
# Run the command on container startup
CMD cron && tail -f /root/cron.log