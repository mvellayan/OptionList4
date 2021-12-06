docker container run -d  -v $(pwd)/IBdata:/IBapp/IBdata ol4 python3 ib_realtime_18.py config/config-aapl.json
docker container run -d  -v $(pwd)/IBdata:/IBapp/IBdata ol4 python3 ib_realtime_18.py config/config-fb.json
