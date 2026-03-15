#!/bin/bash
cd "$(dirname "$0")/.."
PYTHONPATH=app uvicorn api.main:app --reload --port 8000
