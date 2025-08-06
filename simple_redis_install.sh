#!/bin/bash

# 🚀 Simple Redis Installation (Alternative method)
# For when repository issues are persistent

echo "🚀 Simple Redis Installation"
echo "============================"

# Check if Redis is already running
if redis-cli ping &> /dev/null; then
    echo "✅ Redis is already running!"
    exit 0
fi

echo "📦 Installing Redis using snap (alternative method)..."

# Install Redis using snap (doesn't depend on apt repositories)
if command -v snap &> /dev/null; then
    echo "Installing Redis via snap..."
    sudo snap install redis
    
    # Start Redis
    echo "Starting Redis..."
    sudo systemctl start snap.redis.server
    sudo systemctl enable snap.redis.server
    
    # Test Redis
    sleep 2
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis installed and running via snap!"
        redis-cli ping
        exit 0
    fi
fi

echo "📦 Trying manual installation..."

# Download and compile Redis manually
cd /tmp
wget http://download.redis.io/redis-stable.tar.gz
tar xzf redis-stable.tar.gz
cd redis-stable
make

# Install Redis
sudo make install

# Create Redis user and directories
sudo useradd --system --home /var/lib/redis --shell /bin/false redis 2>/dev/null || true
sudo mkdir -p /var/lib/redis /var/log/redis /etc/redis
sudo chown redis:redis /var/lib/redis /var/log/redis

# Create Redis configuration
sudo tee /etc/redis/redis.conf > /dev/null << 'EOF'
bind 127.0.0.1
port 6379
daemonize yes
pidfile /var/run/redis.pid
logfile /var/log/redis/redis.log
dir /var/lib/redis
save 900 1
save 300 10
save 60 10000
EOF

# Create systemd service
sudo tee /etc/systemd/system/redis.service > /dev/null << 'EOF'
[Unit]
Description=Redis In-Memory Data Store
After=network.target

[Service]
User=redis
Group=redis
ExecStart=/usr/local/bin/redis-server /etc/redis/redis.conf
ExecStop=/usr/local/bin/redis-cli shutdown
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start Redis
sudo systemctl daemon-reload
sudo systemctl start redis
sudo systemctl enable redis

# Test Redis
sleep 2
if redis-cli ping &> /dev/null; then
    echo "✅ Redis installed and running manually!"
    redis-cli ping
else
    echo "❌ Manual Redis installation failed"
    exit 1
fi