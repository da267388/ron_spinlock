#!/bin/bash
SERVER="172.16.1.72"
USER="yunhsihsu"

#setup all need package 
sudo apt update -y
sudo apt upgrade -y
sudo apt install -y curl build-essential pkg-config libssl-dev cargo
sudo chmod +x test_client1.sh

#setup all directories
cd $HOME
if [ ! -d "RON_TSP" ]; then
    mkdir RON_TSP
fi
cd ./RON_TSP
if [ ! -d "measurements" ]; then
    mkdir measurements
fi
if [ ! -d "tsp_order" ]; then
    mkdir tsp_order
fi
if [ ! -d "tmp" ]; then
    mkdir tmp
fi
cd $HOME

ssh-keygen -t ed25519
ssh-copy-id -i ~/.ssh/id_ed25519.pub $USER@$SERVER


echo "start measure"
