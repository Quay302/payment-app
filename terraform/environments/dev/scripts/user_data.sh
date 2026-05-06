#!/bin/bash
yum update -y
yum install -y python3 git

cd /home/ec2-user

# clone your repo
git clone https://github.com/YOUR_USERNAME/payment-app.git

cd payment-app/app

# install dependencies
pip3 install flask

