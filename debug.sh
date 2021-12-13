docker container run --network host -it -v $(pwd)/IBdata:/IBapp/IBdata -v $(pwd)/logs:/logs -v  /users/mvellayan/.aws/:/opt/app-root/src/.aws ol4 python3 ib_realtime_18.py config/config-aapl.json
#docker container run --network host -it -v $(pwd)/IBdata:/IBapp/IBdata -v $(pwd)/logs:/logs -v  /users/mvellayan/.aws/:/opt/app-root/src/.aws ol4 /bin/bash
