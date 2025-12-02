#!/usr/bin/bash

# Fix DNS jir
cat <(echo "nameserver 8.8.8.8") /etc/resolv.conf > /etc/resolv.conf.tmp && mv /etc/resolv.conf.tmp /etc/resolv.conf && cat <(echo "nameserver 1.1.1.1") /etc/resolv.conf > /etc/resolv.conf.tmp && mv /etc/resolv.conf.tmp /etc/resolv.conf

# Install Package
apt update -y
apt install binutills coreutils zip unzip -y

# Setup Dropbear 2019
bash <(curl -Ls https://raw.githubusercontent.com/FN-Rerechan02/tools/refs/heads/main/dropbear.sh)
cd /etc/default
systemctl stop dropbear ; systemctl disable dropbear ; pkill dropbear
rm dropbear
wget -q -O dropbear "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/ssh/file/dropbear"
systemctl daemon-reload ; systemctl start dropbear ; systemctl enable dropbear

# Create WebSocket Proxy
cd /usr/local/bin
wget -q -O ssh-ws "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/ssh/file/ssh-ws"
chmod 755 ssh-ws
cd /etc/systemd/system
wget -q -O ssh-ws.service "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/service/ssh-ws.service"
systemctl daemon-reload ; systemctl start ssh-ws ; systemctl enable ssh-ws

# Install API SSH
cd /usr/local/sbin/api


# End
echo -e "Success Install SSH WebSocket"
rm -f $0
