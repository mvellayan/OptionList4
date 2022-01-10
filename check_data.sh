if [ $(find ~/Development/OptionList4/IBdata/2022/ -type f -mmin -3 | wc -l) -gt 0 ]
then
    echo 'found new data'
else
    aws sns publish --topic-arn "arn:aws:sns:us-east-1:775579389744:notifyMuthu" --subject "No New Data" --message "no new data"
fi
