echo "Execution Time: `date`"
cd ~/Development/OptionList4
#docker container ls
#docker ps -f ancestor=ol4
if [ "$(docker ps -f ancestor=ol4 | wc -l)" -eq 0 ]; then
   echo "Nothing running"
else
   echo "Stopping..."
   echo 'Before listing of containers -----------------'
   docker container ls
   /usr/local/bin/docker-compose down
   echo 'After stopping listing of containers-----------------'
   docker container ls
fi
echo ''
echo ''
exit 0
