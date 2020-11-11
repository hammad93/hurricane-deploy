FROM continuumio/anaconda3:2020.07

# Google Artificial Intelligence Platform Api Authentication
COPY ./authentication.json ~/authentication.json
ENV GOOGLE_APPLICATION_CREDENTIALS=~/authentication.json

# Python additional requirements
COPY ./requirements.txt ~/requirements.txt
RUN pip install -r ~/requirements.txt