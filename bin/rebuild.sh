#!/bin/bash
docker compose down -v
docker build --no-cache -t qortal-bwa-image .
docker compose up
