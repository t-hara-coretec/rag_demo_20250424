#!/bin/bash

uvicorn chat_app:app --host 0.0.0.0 --port 8000 --reload
