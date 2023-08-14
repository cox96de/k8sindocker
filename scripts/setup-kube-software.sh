set -ex
# Uncomment the following lines if you are in China
echo 'deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye main contrib non-free
      # deb-src https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye main contrib non-free

      deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-updates main contrib non-free
      # deb-src https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-updates main contrib non-free

      deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-backports main contrib non-free
      # deb-src https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-backports main contrib non-free

      deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bullseye-security main contrib non-free
      # deb-src https://mirrors.tuna.tsinghua.edu.cn/debian-security bullseye-security main contrib non-free

      # deb https://security.debian.org/debian-security bullseye-security main contrib non-free
      # # deb-src https://security.debian.org/debian-security bullseye-security main contrib non-free' > /etc/apt/sources.list

apt-get update
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common

# Install docker & containerd
apt-get update
apt-get install ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Configure containerd
if [ -f /etc/modprobe.d/nf-blacklist.conf ]; then mv /etc/modprobe.d/nf-blacklist.conf /etc/modprobe.d/nf-blacklist.conf-bak; fi
# Reference: https://kubernetes.io/docs/setup/production-environment/container-runtimes/#containerd.
cat <<EOF > /etc/modules-load.d/containerd.conf
overlay
br_netfilter
EOF
modprobe overlay
modprobe br_netfilter
cat <<EOF > /etc/sysctl.d/99-containerd.conf
net.bridge.bridge-nf-call-ip6tables=1
net.bridge.bridge-nf-call-iptables=1
net.ipv6.conf.all.forwarding=1
net.ipv4.ip_forward=1
EOF
sysctl --system

containerd config default > /etc/containerd/config.toml
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
sed -i 's/\[plugins\."io\.containerd\.grpc\.v1\.cri"\.registry\.mirrors\]/\[plugins\."io\.containerd\.grpc\.v1\.cri"\.registry\.mirrors\]\n        \[plugins\."io\.containerd\.grpc\.v1\.cri"\.registry\.mirrors\."docker\.io"\]\n          endpoint = \["docker\.m\.daocloud\.io"\]/' /etc/containerd/config.toml
sed -i 's/\[plugins\."io\.containerd\.grpc\.v1\.cri"\.registry\.mirrors\]/\[plugins\."io\.containerd\.grpc\.v1\.cri"\.registry\.mirrors\]\n        \[plugins\."io\.containerd\.grpc\.v1\.cri"\.registry\.mirrors\."k8s\.gcr\.io"\]\n          endpoint = \["k8s-gcr\.m\.daocloud\.io"\]\n        \[plugins\."io\.containerd\.grpc\.v1\.cri"\.registry\.mirrors\."registry\.k8s\.io"\]\n          endpoint = \["k8s\.m\.daocloud\.io"\]/' /etc/containerd/config.toml
systemctl daemon-reload && systemctl restart containerd

# Install kubernetes

curl https://mirrors.aliyun.com/kubernetes/apt/doc/apt-key.gpg | apt-key add -
cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
deb https://mirrors.aliyun.com/kubernetes/apt/ kubernetes-xenial main
EOF
apt-key adv --keyserver keyserver.ubuntu.com --recv-keys B53DC80D13EDEF05
apt-get update
apt-get install -y kubelet kubeadm kubectl cri-tools

mkdir -p /etc/systemd/system/containerd.service.d/
# Proxy for docker image downloading.
systemctl daemon-reload && systemctl restart containerd
kubeadm config images pull

# Configure ssh
ssh-keygen -A
systemctl restart sshd

cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
echo '
PermitRootLogin yes' >> /etc/ssh/sshd_config
sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart sshd
echo -e 'password\npassword' | passwd  root
