docker container run -d  -v $(pwd)/IBdata:/IBapp/IBdata ol4 python3 model_project_options.py config/config-aapl.json
docker container run -d  -v $(pwd)/IBdata:/IBapp/IBdata ol4 python3 model_project_options.py config/config-fb.json
