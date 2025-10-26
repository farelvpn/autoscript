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

# Make A Directory
mkdir -p /etc/xray/limit/ip/ssh
mkdir -p /etc/xray/limit/ip/vless
mkdir -p /etc/xray/limit/quota/ssh
mkdir -p /etc/xray/limit/database/ssh
mkdir -p /etc/xray/limit/database/vless
mkdir -p /etc/xray/usage/quta/vless
mkdir -p /etc/xray/recovery/ssh
mkdir -p /etc/xray/recovery/vless
mkdir -p /etc/xray/usage/quota/vless
mkdir -p /etc/xray/limit/database/trojan
mkdir -p /etc/xray/usage/quta/trojan
mkdir -p /etc/xray/recovery/trojan
mkdir -p /etc/xray/recovery/trojan
mkdir -p /etc/xray/usage/quota/trojan
mkdir -p /etc/xray/limit/database/vmess
mkdir -p /etc/xray/usage/quta/vmess
mkdir -p /etc/xray/recovery/vmess
mkdir -p /etc/xray/recovery/vmess
mkdir -p /etc/xray/usage/quota/vmess

# Copy Menu
cd /usr/local/sbin
apt update
apt install zip unzip -y
wget -qO menu.zip "https://raw.githubusercontent.com/88PanelSc/sc/main/main.zip"
unzip menu.zip
rm -f menu.zip
chmod +x *
cd api
chmod +x *
cd

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

# Install Squid Proxy
apt install sudo -y
wget -q https://raw.githubusercontent.com/serverok/squid-proxy-installer/master/squid3-install.sh -O squid3-install.sh
sudo bash squid3-install.sh
rm -f squid3-install.sh

if [ -f /etc/squid/squid.conf ]; then
  cd /etc/squid
  find . -type f -name "squid.conf" -exec sed -i 's|http_access allow password|http_access allow all|g' {} +
  sudo sed -i 's/^http_port.*$/http_port 8080/g'  /etc/squid/squid.conf
  systemctl daemon-reload
  systemctl restart squid
elif [ -f /etc/squid3/squid.conf ]; then
  cd /etc/squid3
  find . -type f -name "squid.conf" -exec sed -i 's|http_access allow password|http_access allow all|g' {} +
  sudo sed -i 's/^http_port.*$/http_port 8080/g'  /etc/squid3/squid.conf
  systemctl daemon-reload
  systemctl restart squid3
else
  echo "Konfigurasi squid tidak ditemukan di /etc/squid maupun /etc/squid3"
fi

# Setup OVPN
curl -s https://raw.githubusercontent.com/FN-Rerechan02/ovpn/main/openvpn.sh | bash

# Setup OHP
cd /usr/local/bin
wget -O ohp.zip "https://raw.githubusercontent.com/FN-Rerechan02/ovpn/main/ohpserver-linux32.zip"
unzip ohp.zip
chmod +x ohpserver
rm -f ohp.zip

# Setup Service OHP
cd /etc/systemd/system
cat > /etc/systemd/system/ohp-dropbear.service << END
[Unit]
Description=SSH OHP Redirection Service
Documentation=https://t.me/Rerechan02
After=network.target nss-lookup.target

[Service]
Type=simple
User=root
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart=/usr/local/bin/ohpserver -port 3128 -proxy 127.0.0.1:3128 -tunnel 127.0.0.1:109
Restart=on-failure
LimitNOFILE=infinity

[Install]
WantedBy=multi-user.target
END

cat > /etc/systemd/system/ohp-openvpn.service << END
[Unit]
Description=SSH OHP Redirection Service
Documentation=https://t.me/Rerechan02
After=network.target nss-lookup.target

[Service]
Type=simple
User=root
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart=/usr/local/bin/ohpserver -port 8000 -proxy 127.0.0.1:3128 -tunnel 127.0.0.1:1194
Restart=on-failure
LimitNOFILE=infinity

[Install]
WantedBy=multi-user.target
END

# Service OHP
systemctl daemon-reload
systemctl enable ohp-dropbear ohp-openvpn
systemctl start ohp-dropbear ohp-openvpn
systemctl restart ohp-dropbear ohp-openvpn


# Install Dropbear
apt install dropbear -y
bash <(curl -s https://raw.githubusercontent.com/FN-Rerechan02/tools/refs/heads/main/dropbear.sh)
rm -f /etc/dropbear/dropbear_rsa_host_key
dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key
rm -f /etc/dropbear/dropbear_dss_host_key
dropbearkey -t dss -f /etc/dropbear/dropbear_dss_host_key
rm -f /etc/dropbear/dropbear_ecdsa_host_key
dropbearkey -t ecdsa -f /etc/dropbear/dropbear_ecdsa_host_key
cd /etc/default
rm -f dropbear
wget -qO dropbear "https://raw.githubusercontent.com/88PanelSc/sc/main/files/dropbear"
echo "/bin/false" >> /etc/shells
echo "/usr/sbin/nologin" >> /etc/shells
echo -e "Dev @Rerechan02 Sponsored by @HarisTakiri" > /etc/issue.net
clear
systemctl daemon-reload
/etc/init.d/dropbear restart
clear
cd /root
rm -fr dropbear*

# Install SSH WebSocket
apt install python3 -y
cd /usr/local/bin
wget -qO proxy "https://raw.githubusercontent.com/88PanelSc/sc/main/biner/proxy"
chmod +x proxy
cd /etc/systemd/system
wget -qO ssh-ws.service "https://raw.githubusercontent.com/88PanelSc/sc/main/service/ssh-ws.service"
cd
systemctl daemon-reload
systemctl start ssh-ws.service
systemctl enable ssh-ws.service

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
wget -q -O /etc/xray/config.json "https://raw.githubusercontent.com/88PanelSc/sc/main/files/config.json"
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
wget -qO xray.service "https://raw.githubusercontent.com/88PanelSc/sc/main/service/xray.service"
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
wget -qO /etc/nginx/nginx.conf "https://raw.githubusercontent.com/Rerechan-Team/websocket-proxy/fn_project/nginx.conf"
wget -qO /etc/nginx/fn.conf "https://raw.githubusercontent.com/88PanelSc/sc/main/files/rerechan.conf"
sed -i "s|xxx|${domain}|g" /etc/nginx/fn.conf
systemctl daemon-reload
systemctl start nginx

# Setup Crontab
apt install cron -y

# Setup Auto Backup
echo "* * * * * root xp-ssh" >> /etc/crontab
echo "* * * * * root xp-vless" >> /etc/crontab
echo "* * * * * root xp-vmess" >> /etc/crontab
echo "* * * * * root xp-trojan" >> /etc/crontab
echo "0 * * * * root backup" >> /etc/crontab
echo "0 0 * * * root fixlog" >> /etc/crontab
echo "0 * * * * root cek-ssh" >> /etc/crontab
echo "0 * * * * root cek-vmess" >> /etc/crontab
echo "0 * * * * root cek-vless" >> /etc/crontab
echo "0 * * * * root cek-trojan" >> /etc/crontab

# restart service
systemctl daemon-relaod
systemctl restart cron

# Install Package Lain
curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash
sudo apt-get install speedtest

# Setup Limit IP & Quota
cd /etc/systemd/system
wget -q https://raw.githubusercontent.com/88PanelSc/sc/refs/heads/main/service/quota.service
wget -q https://raw.githubusercontent.com/88PanelSc/sc/refs/heads/main/service/limit-ip-vless.service
wget -q https://raw.githubusercontent.com/88PanelSc/sc/refs/heads/main/service/quota-trojan.service
wget -q https://raw.githubusercontent.com/88PanelSc/sc/refs/heads/main/service/limit-ip-trojan.service
wget -q https://raw.githubusercontent.com/88PanelSc/sc/refs/heads/main/service/quota-vmess.service
wget -q https://raw.githubusercontent.com/88PanelSc/sc/refs/heads/main/service/limit-ip-vmess.service

systemctl daemon-reload
systemctl start quota limit-ip-vless
systemctl enable quota limit-ip-vless
systemctl start quota-trojan limit-ip-trojan
systemctl enable quota-trojan limit-ip-trojan
systemctl start quota-vmess limit-ip-vmess
systemctl enable quota-vmess limit-ip-vmess
cd

# Api Server
cd /usr/local/bin
wget -qO server "https://raw.githubusercontent.com/88PanelSc/sc/main/files/server"
chmod +x server
cd /etc/systemd/system
wget -q https://raw.githubusercontent.com/88PanelSc/sc/main/service/server.service
chmod +x server.service
systemctl darmon-reload

clear
echo -e "clear ; menu" > /root/.profile

# Create Swap
echo -e "Creating Swap Ram"
sh <(curl -s https://raw.githubusercontent.com/FN-Rerechan02/tools/refs/heads/main/swap.sh)
echo -e "Success Create Swap Ram"

clear

# Notification
echo -e " Script Success Install"
rm -fr *.sh
