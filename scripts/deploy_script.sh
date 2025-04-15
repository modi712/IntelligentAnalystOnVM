#!/bin/bash
set -e


# Replace {YOUR_GIT_REOPO_URL} with your actual Git repository URL


GIT_REPO_URL="https://modi712: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@github.com/modi712/IntelligentAnalystOnVM.git"


# Replace {YOUR_PROJECT_MAIN_DIR_NAME} with your actual project directory name
PROJECT_MAIN_DIR_NAME="llmchatbot"

# Clone repository
git clone  "$GIT_REPO_URL" "/home/azureuser/$PROJECT_MAIN_DIR_NAME" 

cd "/home/azureuser/$PROJECT_MAIN_DIR_NAME"

# Make all .sh files executable
chmod +x scripts/*.sh

# Execute scripts for OS dependencies, Python dependencies, Gunicorn, Nginx, and starting the application
./scripts/instance_os_dependencies.sh
./scripts/python_dependencies.sh
./scripts/gunicorn.sh
./scripts/nginx.sh
./scripts/start_app.sh