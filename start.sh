cd ~/Development/OptionList4
docker ps -f ancestor=ol4
if [ "$(docker ps -f ancestor=ol4 | wc -l)" -eq 3 ]; then
   echo "Seems ok"
   #docker ps -f ancestor=ol4
else
   echo "Restarting..."
   docker-compose up
fi
