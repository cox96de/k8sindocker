#!/usr/bin/env python3
import os

from util import run


def main():
    qcow_image = "debian-11-genericcloud-amd64.qcow2"
    url = "https://cloud.debian.org/images/cloud/bullseye/20230802-1460/debian-11-genericcloud-amd64-20230802-1460.qcow2"
    if not os.path.exists(qcow_image):
        run(f"wget -O {qcow_image} -q {url}")


if __name__ == '__main__':
    main()
