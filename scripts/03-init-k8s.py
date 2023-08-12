#!/usr/bin/env python3
import re

from util import *


def main():
    master_ips = ["10.0.1.10", "10.0.1.11", "10.0.1.12"]
    workers = ["10.0.1.13"]
    root = run_output("git rev-parse --show-toplevel")
    echo("Root: " + root)
    echo("generating base qcow2 image")
    run("qemu-img create -f qcow2 -b kube-base.qcow2 -F qcow2 master-00.qcow2 128G")
    run("qemu-img create -f qcow2 -b kube-base.qcow2 -F qcow2 master-01.qcow2 128G")
    run("qemu-img create -f qcow2 -b kube-base.qcow2 -F qcow2 master-02.qcow2 128G")
    run("qemu-img create -f qcow2 -b kube-base.qcow2 -F qcow2 worker-00.qcow2 128G")
    resolv = run_output("cat /etc/resolv.conf")
    # The nameserver in the image controlled by docker-compose is not the host nameserver.
    # It's the one from the docker network.
    # We need to change it to the host nameserver to make the image able to use dns.
    nameserver = re.search(
        r'^\s*nameserver\s*((((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))|(([0-9A-Fa-f]{0,4}:){2,7}([0-9A-Fa-f]{0,4})))\s*$',
        resolv).groups(0)[0]
    echo(f"nameserver: {nameserver}")
    try:
        run("docker-compose up -d")
        ssh_args = f"-i {root}/ssh.private -o StrictHostKeyChecking=no"
        # Change hostname for each node.
        # The hostname is dones not matter but should be distinct in a cluster.
        for idx, ip in enumerate(master_ips):
            try_until_success_or_timeout(
                f"ssh {ssh_args} newsuper@{ip} 'echo success'")
            run(f"ssh {ssh_args} newsuper@{ip} 'sudo bash -c \"echo master{idx} > /etc/hostname\" && sudo reboot now' || true")
        for idx, ip in enumerate(workers):
            try_until_success_or_timeout(
                f"ssh {ssh_args} newsuper@{ip} 'echo success'")
            run(f"ssh {ssh_args} newsuper@{ip} 'sudo bash -c \"echo worker{idx} > /etc/hostname\" && sudo reboot now' || true")
        try_until_success_or_timeout(
            f"ssh {ssh_args} newsuper@{master_ips[0]} 'echo success'")
        echo("setup first master")
        run(f"ssh {ssh_args} newsuper@{master_ips[0]} 'sudo bash -c \"echo nameserver {nameserver} >> /etc/resolv.conf\"'")
        output = run_output(f"ssh {ssh_args} newsuper@{master_ips[0]} 'sudo kubeadm init "
                            "--apiserver-advertise-address 0.0.0.0 "
                            "--apiserver-bind-port 6443 "
                            f"--control-plane-endpoint {master_ips[0]} "
                            "--cert-dir /etc/kubernetes/pki "
                            "--pod-network-cidr 172.20.0.0/16,fdff:ffff:ffff::/48 "
                            "--service-cidr 172.21.0.0/16,fdff:ffff:fffe::/108 "
                            "--service-dns-domain cluster.local "
                            "--upload-certs'")
        token = re.search(r'--token (.*?)\s', output).group(1)
        cert_hash = re.search(r'--discovery-token-ca-cert-hash (.*?)\s', output).group(1)
        cert_key = re.search(r'--certificate-key (.*?)\s', output).group(1)
        for ip in master_ips[1:]:
            echo(f"setup next master {ip}")
            run(f"ssh {ssh_args} newsuper@{ip} 'sudo bash -c \"echo nameserver {nameserver} >> /etc/resolv.conf\"'")
            command = f"kubeadm join {master_ips[0]}:6443 --token {token} --discovery-token-ca-cert-hash {cert_hash} --control-plane --certificate-key {cert_key}"
            run(f"ssh {ssh_args} newsuper@{ip} 'sudo {command}'")
        for ip in workers:
            echo(f"setup next worker {ip}")
            run(f"ssh {ssh_args} newsuper@{ip} 'sudo bash -c \"echo 192.168.31.1 >> /etc/resolv.conf\"'")
            command = f"kubeadm join {master_ips[0]}:6443 --token {token} --discovery-token-ca-cert-hash {cert_hash}"
            run(f"ssh {ssh_args} newsuper@{ip} 'sudo {command}'")
    finally:
        run(f"docker-compose down")


if __name__ == '__main__':
    main()
# [plugins]
#  [plugins."io.containerd.grpc.v1.cri".registry]
#    [plugins."io.containerd.grpc.v1.cri".registry.mirrors]
#      [plugins."io.containerd.grpc.v1.cri".registry.mirrors."k8s.gcr.io"]
#        endpoint = ["registry.aliyuncs.com/google_containers"]
