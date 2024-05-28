#!/bin/bash

# Load environment variables
if [ -f "$1" ]; then
  export $(cat $1 | sed 's/#.*//g' | xargs)
else
  echo "Environment file $1 not found."
  exit 1
fi

service=$3

# Define the operations
case $2 in
  start)
    if [ -z "$service" ]; then
      docker-compose up -d
    else
      docker-compose up -d $service
    fi
    ;;
  down)
    if [ -z "$service" ]; then
      docker-compose down
    else
      docker-compose stop $service
    fi
    ;;
  reset)
    if [ -z "$service" ]; then
      docker-compose down -v
      docker-compose up -d
    else
      docker-compose rm -fsv $service
      docker-compose up -d $service
    fi
    ;;
  logs)
    if [ -z "$service" ]; then
      docker-compose logs -f
    else
      docker-compose logs -f $service
    fi
    ;;
  *)
    echo "Valid commands are: start, down, reset, logs"
    ;;
esac
