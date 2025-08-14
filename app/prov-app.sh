#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

echo "Updating package list..."
apt-get update -y
echo "Package list updated."
echo

echo "Upgrading packages..."
apt-get upgrade -y
echo "Upgrade complete."
echo

echo "Installing Nginx..."
apt-get install nginx -y
echo "Nginx installed."
echo

sudo sed -i 's|try_files \$uri \$uri/ =404;|proxy_pass http://localhost:3000;|' /etc/nginx/sites-available/default

systemctl restart nginx

echo "Installing Node.js v20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
echo "Node.js version: $(node -v)"
echo

echo "Installing PM2 globally..."
npm install -g pm2
echo "PM2 installed."
echo

echo "Cloning Sparta test app "
git clone https://github.com/Geodude132/tech508-george-sparta-app.git repo
echo "Repo cloned."
echo

echo "Setting up environment..."
cd repo/app
export DB_HOST=mongodb://172.31.24.85:27017/posts
echo "Environment variable DB_HOST set."
echo

echo "Installing app dependencies..."
npm install --no-fund --no-audit
echo "Dependencies installed."
echo

echo "Stopping any previous app instances (if any)..."
pm2 delete sparta-app || true
echo

echo "Starting app using PM2..."
pm2 start app.js --name sparta-app
pm2 save
echo "App started with PM2."
echo

echo "Public IP address:"
curl -s http://checkip.amazonaws.com
echo
