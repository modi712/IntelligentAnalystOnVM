#!/usr/bin/bash

# Replace {YOUR_PROJECT_MAIN_DIR_NAME} with your actual project directory name
PROJECT_MAIN_DIR_NAME="llmchatbot"

# Copy gunicorn socket and service files
sudo cp "/home/azureuser/$PROJECT_MAIN_DIR_NAME/gunicorn/gunicorn.socket" "/etc/systemd/system/llmchatbot-gunicorn.socket"
sudo cp "/home/azureuser/$PROJECT_MAIN_DIR_NAME/gunicorn/gunicorn.service" "/etc/systemd/system/llmchatbot-gunicorn.service"

# Start and enable Gunicorn service
sudo systemctl start llmchatbot-gunicorn.service
sudo systemctl enable llmchatbot-gunicorn.service