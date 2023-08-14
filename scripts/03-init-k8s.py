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
    try:
        run("docker-compose up -d")
        ssh_args = f"-i {root}/ssh.private -o StrictHostKeyChecking=no"
        def run_in_vm(ip: str, command: str, runner=run):
            return runner(f"ssh {ssh_args} newsuper@{ip} {command}")
        # Change hostname for each node.
        # The hostname is dones not matter but should be distinct in a cluster.
        for idx, ip in enumerate(master_ips):
            run_in_vm(ip, "'echo success'", try_until_success_or_timeout)
            run_in_vm(ip, f"'sudo bash -c \"echo master{idx} > /etc/hostname\" && sudo reboot now' || true")
        for idx, ip in enumerate(workers):
            run_in_vm(ip, "'echo success'", try_until_success_or_timeout)
            run_in_vm(ip, f"'sudo bash -c \"echo worker{idx} > /etc/hostname\" && sudo reboot now' || true")
        run_in_vm(master_ips[0], "'echo success'", try_until_success_or_timeout)
        echo("setup first master")
        output = run_in_vm(master_ips[0], "'sudo kubeadm init "
                                          "--apiserver-advertise-address 0.0.0.0 "
                                          "--apiserver-bind-port 6443 "
                                          f"--control-plane-endpoint {master_ips[0]} "
                                          "--cert-dir /etc/kubernetes/pki "
                                          "--pod-network-cidr 172.20.0.0/16,fdff:ffff:ffff::/48 "
                                          "--service-cidr 172.21.0.0/16,fdff:ffff:fffe::/108 "
                                          "--service-dns-domain cluster.local "
                                          "--upload-certs'", run_output)
        token = re.search(r'--token (.*?)\s', output).group(1)
        cert_hash = re.search(r'--discovery-token-ca-cert-hash (.*?)\s', output).group(1)
        cert_key = re.search(r'--certificate-key (.*?)\s', output).group(1)
        run_in_vm(master_ips[0], "'sudo mkdir -p /root/.kube && sudo cp /etc/kubernetes/admin.conf /root/.kube/config'")
        for ip in master_ips[1:]:
            echo(f"setup next master {ip}")

            command = f"kubeadm join {master_ips[0]}:6443 --token {token} --discovery-token-ca-cert-hash {cert_hash} --control-plane --certificate-key {cert_key}"
            run_in_vm(ip, f"'sudo {command}'")
            run_in_vm(ip, "'sudo mkdir -p /root/.kube && sudo cp /etc/kubernetes/admin.conf /root/.kube/config'")
        for ip in workers:
            echo(f"setup next worker {ip}")
            command = f"kubeadm join {master_ips[0]}:6443 --token {token} --discovery-token-ca-cert-hash {cert_hash}"
            run_in_vm(ip, f"'sudo {command}'")
        run(f"ssh {ssh_args} newsuper@{master_ips[0]} 'sudo kubectl get nodes'")
        for ip in workers:
            run_in_vm(ip, "'sudo shutdown now' || true")
        for ip in master_ips:
            run_in_vm(ip, "'sudo shutdown now' || true")
        echo("completed")

    finally:
        run(f"docker-compose down")


if __name__ == '__main__':
    main()
