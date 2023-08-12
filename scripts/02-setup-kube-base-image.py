#!/usr/bin/env python3
from util import *


def main():
    docker_container_name = "init-script"
    root = run_output("git rev-parse --show-toplevel")
    echo("Root: " + root)
    echo("generating base qcow2 image")
    run("qemu-img create -f qcow2 -b debian-11-genericcloud-amd64.qcow2 -F qcow2 kube-base.qcow2 128G")
    echo("generate cloud-init iso")
    run(f"genisoimage -output cloudinit.iso -volid cidata -joliet -rock "
        f"{root}/cloud-init/meta-data "
        f"{root}/cloud-init/user-data")
    try:
        run(f"docker run --name {docker_container_name} --rm "
            "--privileged "
            f"-v {root}/scripts:/images/ "
            "-v /tmp/console/:/tmp "
            "-d "
            "cox96de/containervm:master "
            "-- "
            "qemu-system-x86_64 "
            "-nodefaults "
            "--nographic "
            "-display none "
            "-smp 4,sockets=1,cores=4,threads=1 "
            "-m 4096M "
            "-device virtio-balloon-pci,id=balloon0 "
            "-drive file=/images/kube-base.qcow2,format=qcow2,if=virtio,aio=threads,media=disk,cache=unsafe,snapshot=off "
            "-drive file=/images/cloudinit.iso,media=cdrom,format=raw,readonly=on,if=ide,aio=threads "
            "-device VGA "
            "-serial chardev:serial0 "
            "-chardev socket,id=serial0,path=/tmp/console.sock,server=on,wait=off")
        time.sleep(3)
        container_ip = run_output(
            "docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' " + docker_container_name)
        echo("container ip: " + container_ip)
        run(f"chmod 600 {root}/ssh.private")
        ssh_args = f"-i {root}/ssh.private -o StrictHostKeyChecking=no"
        try_until_success_or_timeout(
            f"ssh {ssh_args} newsuper@{container_ip} 'echo success'")
        run(f"scp {ssh_args} {root}/scripts/setup-kube-software.sh newsuper@{container_ip}:/tmp/setup-kube-software.sh")
        run(f"ssh {ssh_args} newsuper@{container_ip} 'sudo bash /tmp/setup-kube-software.sh'")
    finally:
        run(f"docker stop {docker_container_name}")


if __name__ == '__main__':
    main()
