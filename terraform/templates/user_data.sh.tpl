#!/bin/bash
# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# Cloud-Init Bootstrap Script (4GB Swap, Memory Tuning, Docker, AWS CLI v2, UFW)
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

set -euo pipefail

echo "=========================================="
echo "1. Creating 4GB Swap Space"
echo "=========================================="
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

echo "=========================================="
echo "2. Kernel Memory Tuning"
echo "=========================================="
cat <<EOF > /etc/sysctl.d/99-cerms-memory.conf
vm.swappiness=10
vm.vfs_cache_pressure=50
net.core.somaxconn=4096
EOF
sysctl -p /etc/sysctl.d/99-cerms-memory.conf

echo "=========================================="
echo "3. Installing System Dependencies & AWS CLI v2"
echo "=========================================="
apt-get update && apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg unzip ufw git software-properties-common

# Install AWS CLI v2 (Architecture Adaptive)
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ]; then
  curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
else
  curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
fi
unzip -q awscliv2.zip
./aws/install
rm -rf awscliv2.zip aws/

echo "=========================================="
echo "3.1. Installing Native AWS SSM Agent (.deb)"
echo "=========================================="
snap remove amazon-ssm-agent || true
mkdir -p /tmp/ssm
curl -s "https://s3.ap-south-1.amazonaws.com/amazon-ssm-ap-south-1/latest/debian_amd64/amazon-ssm-agent.deb" -o /tmp/ssm/amazon-ssm-agent.deb
dpkg -i /tmp/ssm/amazon-ssm-agent.deb
systemctl enable amazon-ssm-agent
systemctl restart amazon-ssm-agent
rm -rf /tmp/ssm


echo "=========================================="
echo "4. Installing Docker & Docker Compose v2"
echo "=========================================="
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

echo "=========================================="
echo "5. UFW Firewall Configuration"
echo "=========================================="
ufw default deny incoming
ufw default allow outgoing
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "=========================================="
echo "6. Configuring Nightly Disaster Recovery Cron"
echo "=========================================="
mkdir -p /opt/cerms/scripts
(crontab -l 2>/dev/null | grep -v "nightly_db_backup.sh" ; echo "0 2 * * * /bin/bash /opt/cerms/scripts/nightly_db_backup.sh >> /var/log/cerms_backup.log 2>&1") | crontab -

echo "CERMS Cloud-Init Bootstrap Completed Successfully!"