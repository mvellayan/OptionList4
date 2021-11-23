echo "Execution Time: `date`"
cd ~/Development/OptionList4
#docker container ls
#docker ps -f ancestor=ol4
if [ "$(docker ps -f ancestor=ol4 | wc -l)" -eq 3 ]; then
   echo "Seems ok"
   docker ps -f ancestor=ol4
else
   echo "Restarting..."
   echo 'Before listing of containers -----------------'
   docker container ls
   /usr/local/bin/docker-compose down
   /usr/local/bin/docker-compose up --detach
   echo 'After re/start listing of containers-----------------'
   docker container ls
fi
echo ''
echo ''
