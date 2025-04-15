# Django Chatbot Application Deployment Guide

This guide provides step-by-step instructions for deploying a Django-based chatbot application on a Linux Virtual Machine (VM) using Gunicorn and Nginx. 

## Table of Contents
- [Prerequisites](#prerequisites)
- [Setting Up the Linux VM](#setting-up-the-linux-vm)
- [Cloning and Configuring the Application](#cloning-and-configuring-the-application)
- [Setting Up the Virtual Environment](#setting-up-the-virtual-environment)
- [Configuring Gunicorn](#configuring-gunicorn)
- [Configuring Nginx](#configuring-nginx)
- [Security Considerations](#security-considerations)

## Prerequisites

- A Linux VM (Ubuntu 20.04+ recommended)
- Domain name (optional)
- Git installed on your local machine
- SSH access to your VM
- Basic understanding of Linux commands

## Setting Up the Linux VM

### 1. Update the system
```bash
sudo apt update
sudo apt upgrade -y
```
### 2. Install necessary packages
```bash
sudo apt install -y python3-pip python3-venv git nginx
```
### 3. Create a new user (optional but recommended)
```bash
sudo adduser azureuser
sudo usermod -aG sudo azureuser
```

## Cloning and Configuring the Application

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/llmchatbot.git
cd llmchatbot
```
### 2. Configure environment variables
 ### Create a .env file in the project root:

```bash
touch .env
```
### Add the following environment variables:

```bash
SECRET_KEY=your_secure_secret_key
DEBUG=False
ALLOWED_HOSTS=your_domain_or_ip,localhost,127.0.0.1
```

## Setting Up the Virtual Environment
### 1. Create and activate virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```
### 2. Install dependencies
```bash
pip install -r requirements.txt
```
### 3. Collect static files
```bash
python manage.py collectstatic --noinput
```

## Configuring Gunicorn
### 1. Install Gunicorn
```bash
pip install gunicorn
```
### 2. Create Gunicorn socket file
```bash
sudo nano /etc/systemd/system/gunicorn.socket
```
### Add the following content:
```ini
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```

### 3. Create Gunicorn service file
```bash
sudo nano /etc/systemd/system/gunicorn.service
```
### Add the following content:
```ini
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=azureuser
Group=www-data
WorkingDirectory=/home/azureuser/llmchatbot
ExecStart=/home/azureuser/llmchatbot/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          llmchatbot.wsgi:application

[Install]
WantedBy=multi-user.target
```

### 4. Start and enable Gunicorn
```bash
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
```

## Configuring Nginx
### 1. Create Nginx configuration file
```bash
sudo nano /etc/nginx/sites-available/llmchatbot
```
### Add the following content:
```nginx
server {
    listen 80;
    server_name your_domain_or_ip;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /home/azureuser/llmchatbot;
    }

    location /media/ {
        root /home/azureuser/llmchatbot;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_redirect off;
        client_max_body_size 20M;
    }
}
```
### 2. Enable the Nginx configuration
```bash
sudo ln -s /etc/nginx/sites-available/llmchatbot /etc/nginx/sites-enabled
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

## Security Considerations
### 1. Set proper file permissions
```bash
chmod 600 .env
sudo chown -R azureuser:www-data /home/azureuser/llmchatbot
sudo chmod -R 755 /home/azureuser/llmchatbot
```
### 2. Configure HTTPS with Let's Encrypt (recommended for production)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain
```

## Example Deployment
### Our example deployment can be accessed at http://4.240.75.126/

## Maintenance and Updates
### Updating the application
```bash
cd /home/azureuser/llmchatbot
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```