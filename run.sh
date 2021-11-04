docker run -d -it -v $(pwd)/IBdata:/IBapp/IBdata ol4 python3 realtime_data_collector.py config/config-aapl.json
docker run -r -it -v $(pwd)/IBdata:/IBapp/IBdata ol4 python3 realtime_data_collector.py config/config-fb.json
