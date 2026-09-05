#!/bin/bash
set -e

CIDS=$(sudo su - -c "docker ps -q -f name=gzh-chroma -f name=gzh-expert-app -f name=gzh-expert-db -f name=gzh-worker -f name=frpc" | tr '\n' ' ' | sed 's/ $//')
echo "to stop: $CIDS"

if [ -z "$CIDS" ]; then
    echo "no matching containers"
    exit 0
fi

sudo su - -c "docker stop $CIDS"

sleep 1
echo "---after---"
sudo su - -c "docker ps -a -f name=gzh-chroma -f name=gzh-expert-app -f name=gzh-expert-db -f name=gzh-worker -f name=frpc --format 'table {{.Names}}\t{{.Status}}'"
