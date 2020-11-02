FROM tensorflow/serving:2.3.0-gpu

# model zip folder
COPY '2020-11-01T07 32 40.125860.zip' ~/model.zip
RUN unzip model.zip
RUN rm model.zip
