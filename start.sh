echo "Execution Time: `date`"
cd ~/Development/OptionList4
echo 'Before -----------------'
docker container ls
docker ps -f ancestor=ol4
#if [ "$(docker ps -f ancestor=ol4 | wc -l)" -eq 3 ]; then
#   echo "Seems ok"
   #docker ps -f ancestor=ol4
#else
   echo "Restarting..."
   cd ~/Development/OptionList4
   /usr/local/bin/docker-compose down
   /usr/local/bin/docker-compose up --detach
#fi
echo 'After re/start-----------------'
docker container ls
echo ''
echo ''
