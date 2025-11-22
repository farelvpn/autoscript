#!/bin/bash
clear

# Update & install package
apt update
apt install wget curl openssl sudo binutils coreutils gnupg bc vnstat -y
apt install sudo -y
apt install htop lsof -y
apt install jq -y
apt install python3 -y

# Fix Multi Collor
apt install ruby -y
apt install lolcat -y
gem install lolcat

# Fix DNS
cat <(echo "nameserver 8.8.8.8") /etc/resolv.conf > /etc/resolv.conf.tmp && mv /etc/resolv.conf.tmp /etc/resolv.conf && cat <(echo "nameserver 1.1.1.1") /etc/resolv.conf > /etc/resolv.conf.tmp && mv /etc/resolv.conf.tmp /etc/resolv.conf

# Fix Port OpenSSH
cd /etc/ssh
find . -type f -name "*sshd_config*" -exec sed -i 's|#Port 22|Port 22|g' {} +
echo -e "Port 3303" >> sshd_config
cd
systemctl daemon-reload
systemctl restart ssh
systemctl restart sshd

# Create Api Repo
mkdir -p /usr/local/sbin/api

# Direktori untuk Trojan
mkdir -p /etc/xray/database/trojan
mkdir -p /etc/xray/limit/quota/trojan
mkdir -p /etc/xray/usage/quota/trojan

# Direktori untuk VMess
mkdir -p /etc/xray/database/vmess
mkdir -p /etc/xray/limit/quota/vmess
mkdir -p /etc/xray/usage/quota/vmess

# Direktori untuk VLESS
mkdir -p /etc/xray/database/vless
mkdir -p /etc/xray/limit/quota/vless
mkdir -p /etc/xray/usage/quota/vless


# Ini firewall
apt update
apt install ufw sudo -y
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 1:65535/udp
sudo ufw allow 1:65535/tcp
sudo ufw allow from any to any port 1:65535 proto tcp
sudo ufw allow from any to any port 1:65535 proto udp
sudo ufw status verbose

# Set Data Domain Server
clear
echo -e "
+++++++++++++++++++++++++++++++++++++++++++++++++++++++
            INPUT DOMAIN FOR SERVER
+++++++++++++++++++++++++++++++++++++++++++++++++++++++
"

while true; do
    read -p "Input: " domain
    if [[ -n "$domain" ]]; then
        break
    else
        echo -e "\e[31m[!] Domain tidak boleh kosong, silakan ulangi.\e[0m"
    fi
done

echo -e "\e[32m[OK]\e[0m Domain set -> $domain"

clear
echo -e "$domain" > /etc/xray/domain

# Install BadVPN / UDPGW for Support Call & Video Call
cd /usr/local/bin
OS=`uname -m`;
sudo wget -O /usr/local/bin/badvpn "https://raw.githubusercontent.com/daybreakersx/premscript/master/badvpn-udpgw"
if [ "$OS" == "x86_64" ]; then
  sudo wget -O /usr/local/bin/badvpn "https://raw.githubusercontent.com/daybreakersx/premscript/master/badvpn-udpgw64"
fi
chmod +x badvpn
cd /etc/systemd/system
wget -qO badvpn.service "https://raw.githubusercontent.com/88PanelSc/sc/main/service/badvpn.service"
cd
systemctl daemon-reload
systemctl start badvpn.service
systemctl enable badvpn.service

# Install Xray
mkdir -p /usr/local/share/xray
wget -q -O /usr/local/share/xray/geosite.dat "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat" >/dev/null 2>&1
wget -q -O /usr/local/share/xray/geoip.dat "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat" >/dev/null 2>&1
chmod +x /usr/local/share/xray/*
wget -q -O /etc/xray/config.json "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/files/config.json"
cd /etc/xray
uuid=$(cat /proc/sys/kernel/random/uuid)
sed -i "s|xxxxx|${uuid}|g" /etc/xray/config.json
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install -u www-data --version 25.8.31

# Fix Service Xray
cd /var/log
rm -r xray
mkdir -p xray
sudo chown -R root:root /var/log/xray
sudo touch /var/log/xray/access.log /var/log/xray/error.log
sudo chmod 644 /var/log/xray/*.log
cd /etc/systemd/system
systemctl stop xray.service
systemctl disable xray.service
rm -fr xray*
wget -qO xray.service "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/service/xray.service"
systemctl enable xray
systemctl start xray
systemctl restart xray

# Set
domain=$(cat /etc/xray/domain)

# Nginx & Certificate Setup
apt install socat -y
apt install lsof socat certbot -y
port=$(lsof -i:80 | awk '{print $1}')
systemctl stop apache2
systemctl disable apache2
pkill $port
yes Y | certbot certonly --standalone --preferred-challenges http --agree-tos --email dindaputri@rerechanstore.eu.org -d $domain 
cp /etc/letsencrypt/live/$domain/fullchain.pem /etc/xray/xray.crt
cp /etc/letsencrypt/live/$domain/privkey.pem /etc/xray/xray.key
cd /etc/xray
chmod 644 /etc/xray/xray.key
chmod 644 /etc/xray/xray.crt

# Setup Nginx
bash <(curl -s https://raw.githubusercontent.com/FN-Rerechan02/tools/refs/heads/main/nginx.sh)
systemctl stop nginx
wget -qO /etc/nginx/nginx.conf "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/files/nginx.conf"
wget -qO /etc/nginx/conf.d/default.conf "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/files/default.conf"
sed -i "s|xxx|${domain}|g" /etc/nginx/conf.d/default.conf
systemctl daemon-reload
systemctl start nginx

# Setup Crontab
apt install cron -y

# Setup Code Backup & Restore
cd /usr/local/sbin
wget -O backup "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/backup/backup.py"
wget -O restore "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/backup/restore.py"
chmod +x backup restore

# Setup Auto Backup
echo "0 * * * * root backup" >> /etc/crontab

# restart service
systemctl daemon-relaod
systemctl restart cron

# Install Package Lain
curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash
sudo apt-get install speedtest

# Setup Trojan
cd /usr/local/sbin/api/
wget -O add-trojan "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/trojan/add-trojan.py"
wget -O add-quota-trojan "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/trojan/add-quota-trojan.py"
wget -O cek-trojan "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/trojan/cek-trojan.py"
wget -O delete-trojan "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/trojan/delete-trojan.py"
chmod +x *trojan
cd /usr/local/sbin
wget -O loop-quota-trojan "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/trojan/loop-quota-trojan.py"
wget -O quota-trojan "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/trojan/quota-trojan.py"
chmod +x quota-trojan loop-quota-trojan
cd /etc/systemd/system
wget -q -O quota-trojan.service "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/service/quota-trojan.service"
systemctl daemon-reload
systemctl enable quota-trojan
systemctl start quota-trojan

# Setup Vmess
cd /usr/local/sbin/api
wget -O add-vmess "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/vmess/add-vmess.py"
wget -O add-quota-vmess "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/vmess/add-quota-vmess.py"
wget -O cek-vmess "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/vmess/cek-vmess.py"
wget -O delete-vmess "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/vmess/delete-vmess.py"
chmod +x *vmess
cd /usr/local/sbin
wget -O loop-quota-vmess "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/vmess/loop-quota-vmess.py"
wget -O quota-vmess "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/vmess/quota-vmess.py"
chmod +x quota-vmess loop-quota-vmess
cd /etc/systemd/system
wget -q -O quota-vmess.service "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/service/quota-vmess.service"
systemctl daemon-reload
systemctl enable quota-vmess
systemctl start quota-vmess

# Setup Vless
cd /usr/local/sbin/api/
wget -O add-vless "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/vless/add-vless.py"
wget -O add-quota-vless "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/vless/add-quota-vless.py"
wget -O cek-vless "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/vless/cek-vless.py"
wget -O delete-vless "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/vless/delete-vless.py"
chmod +x *vless
cd /usr/local/sbin
wget -O loop-quota-vless "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/vless/loop-quota-vless.py"
wget -O quota-vless "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/vless/quota-vless.py"
chmod +x quota-vless loop-quota-vless
cd /etc/systemd/system
wget -q -O quota-vless.service "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/service/quota-vless.service"
systemctl daemon-reload
systemctl enable quota-vless
systemctl start quota-vless

# Api Server
cd /usr/local/bin
wget -qO server "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/files/server-api"
chmod +x server
cd /etc/systemd/system
wget -q -O server.service "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/service/server.service"
chmod +x server.service
systemctl daemon-reload
cd /usr/local/sbin
wget -O menu-api "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/menu/menu-api.py"
chmod +x menu-api
cd

# Menu Tambahan
cd /usr/local/sbin
wget -O menu-domain "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/menu/menu-domain.py"
wget -O telegram-info "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/menu/telegram-info.py"
wget -O versi-xray "https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/menu/versi-xray.py"
chmod +x menu-domain telegram-info versi-xray

# Create Swap
echo -e "Creating Swap Ram"
sh <(curl -s https://raw.githubusercontent.com/FN-Rerechan02/tools/refs/heads/main/swap.sh)
echo -e "Success Create Swap Ram"

clear

# Notification
echo -e " Script Success Install"
rm -fr *.sh
