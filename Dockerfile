#FROM python:3.9.7-bullseye
FROM centos/python-38-centos7:20210726-fad62e9
USER root

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

WORKDIR /IBapp/IBdata
WORKDIR /IBapp
RUN chmod +w -R /IBapp

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN echo 'Docker!' | passwd --stdin root
CMD [ "python3", "realtime_data_collector.py", "config/config-fb.json" ]
