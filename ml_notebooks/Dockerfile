# FROM jupyter/datascience-notebook:julia-1.7.0
# FROM julia:1.6.4-buster
# FROM bitnami/jupyter-base-notebook:f2ecf041b924

FROM tensorflow/tensorflow:latest-jupyter

#USER root

# RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
# RUN unzip awscliv2.zip
# RUN ./aws/install

WORKDIR /IBapp

COPY requirements_ml.txt .
RUN pip install -r ./requirements_ml.txt
COPY jupyter_notebook_config.py /root/.jupyter/

# CMD [ "python3", "realtime_data_collector.py", "config/config-fb.json" ]
