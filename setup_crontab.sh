#!/bin/bash

cat <<EOF | tee process_uploads.sh
    cd /var/www/html/wp-content/python
    python3 process_uploads.py
EOF

crontab -l > mycron
#echo new cron into cron file
(crontab -u root -l ; echo "*/5  * * * * . /var/www/html/wp-content/wp-pdftotext-upload-process-python/process_uploads.sh") | crontab -u root -
# echo "*/5  * * * * . /var/www/html/wp-content/python/process_uploads.sh" >> mycron
#install new cron file
crontab mycron
rm mycron

