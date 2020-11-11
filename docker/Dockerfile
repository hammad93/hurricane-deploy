FROM continuumio/anaconda3:2020.07

# Google Artificial Intelligence Platform Api Authentication
COPY authentication.json /root/
ENV GOOGLE_APPLICATION_CREDENTIALS=/root/authentication.json

# SMTP credentials
COPY credentials.csv /root/

# Python additional requirements
COPY requirements.txt /root/
RUN pip install -r /root/requirements.txt