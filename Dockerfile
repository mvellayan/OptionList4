#FROM python:3.9.7-bullseye
FROM centos/python-38-centos7:20210726-fad62e9
USER root

WORKDIR /IBapp/IBdata
WORKDIR /IBapp

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python3", "realtime_data_collector.py", "config/config-fb.json" ]
