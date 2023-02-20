FROM continuumio/anaconda3

# SMTP credentials

COPY credentials.csv /root/

# Python additional requirements
RUN apt-get install -y python-dev
COPY requirements.txt /root/
RUN pip install -r /root/requirements.txt

# Conda
RUN conda install -y mysqlclient

# Add git repository
RUN git clone --single-branch --branch master https://github.com/hammad93/hurricane-deploy.git

# Setup cron job
RUN apt-get --allow-releaseinfo-change update && apt-get -y install cron
RUN apt-get install -y gnupg2

# Install Tensorflow Serve
RUN apt-get install -y sudo
RUN echo "deb [arch=amd64] http://storage.googleapis.com/tensorflow-serving-apt stable tensorflow-model-server tensorflow-model-server-universal" | sudo tee /etc/apt/sources.list.d/tensorflow-serving.list && \
curl https://storage.googleapis.com/tensorflow-serving-apt/tensorflow-serving.release.pub.gpg | sudo apt-key add -
RUN apt-get update && apt-get install tensorflow-model-server

# Entrypoint
ADD entrypoint.sh /root/entrypoint.sh
RUN chmod +x /root/entrypoint.sh
ENTRYPOINT /root/entrypoint.sh
