#!/bin/bash
cd /home/kevin/kantorteman/backend
export $(grep -v '^#' .env | xargs)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
