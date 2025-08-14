#!/bin/bash

# Update system
echo "Updating system..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "Installing dependencies..."
sudo apt install gnupg curl -y

# Add MongoDB GPG key
echo "Adding MongoDB GPG key..."
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor --yes

# Add MongoDB repo (Ubuntu 22.04 = jammy)
echo "Adding MongoDB repository..."
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Update packages
echo "Updating package list..."
sudo apt update

# Install MongoDB
echo "Installing MongoDB..."
sudo apt install -y \
   mongodb-org=7.0.22 \
   mongodb-org-database=7.0.22 \
   mongodb-org-server=7.0.22 \
   mongodb-mongosh \
   mongodb-org-shell=7.0.22 \
   mongodb-org-mongos=7.0.22 \
   mongodb-org-tools=7.0.22 \
   mongodb-org-database-tools-extra=7.0.22

# Enable external access
echo "Configuring MongoDB to allow external connections..."
sudo cp /etc/mongod.conf /etc/mongod.conf.bak
sudo sed -i '/^\s*bindIp:/s/127\.0\.0\.1/0.0.0.0/' /etc/mongod.conf
sudo sed -i '/security:/,+1d' /etc/mongod.conf

# Start MongoDB
echo "Restarting MongoDB..."
sudo systemctl restart mongod
sudo systemctl enable mongod

# Optional: short delay to ensure service is up
sleep 10

# Show bindIp setting for logs
grep bindIp /etc/mongod.conf

echo "MongoDB setup complete."
