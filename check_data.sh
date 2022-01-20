if [ $(find ~/Development/OptionList4/IBdata/2022/ -type f -mmin -3 | grep AAPL | wc -l) -gt 0 ]
then
    echo 'found new AAPL data'
else
    /usr/local/bin/aws sns publish --topic-arn "arn:aws:sns:us-east-1:775579389744:notifyMuthu" --subject "No New AAPL Data" --message "no new AAPL data"
fi
#
#
if [ $(find ~/Development/OptionList4/IBdata/2022/ -type f -mmin -3 | grep FB | wc -l) -gt 0 ]
then
    echo 'found new FB data'
else
    /usr/local/bin/aws sns publish --topic-arn "arn:aws:sns:us-east-1:775579389744:notifyMuthu" --subject "No New FB Data" --message "no new FB data"
fi
