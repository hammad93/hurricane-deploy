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

# Entrypoint
ADD entrypoint.sh /root/entrypoint.sh
RUN chmod +x /root/entrypoint.sh
ENTRYPOINT /root/entrypoint.sh