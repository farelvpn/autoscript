#!/bin/bash

echo -e "Process Setup UDP Custom Server"
slep 2
clear


# Install Binary
cd /usr/local/bin
wget -q -O https://github.com/Rerechan02/UDP/raw/d0ebcc4b65a4ac3dffc3739df402a36d7297ef08/bin/udp-custom-linux-amd64
chmod +x udp-custom-linux-amd64
cd

# Create JSON
mkdir -p /etc/udp/custom
cd /etc/udp/custom
cat <<EOF > config.json
{
  "listen": ":36712",
  "stream_buffer": 33554432,
  "receive_buffer": 83886080,
  "auth": {
    "mode": "passwords"
  }
}
EOF
chmod +x config.json

# Create Service
cd /etc/systemd/system
cat <<EOF > udp-custom.service
[Unit]
Description=UDP Custom Server
After=network.target

[Service]
User=root
WorkingDirectory=/etc/udp/custom
ExecStart=/usr/local/bin/udp-custom-linux-amd64 server -exclude 7300
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now udp-custom
systemctl start udp-custom

# Done
echo -e "UDP Custom Server Setup Done!"
rm -f $0
