# ----- sender.py ------
import time
#!/usr/bin/env python

from socket import *
import sys
import hashlib

def get_digest(file_path):
    h = hashlib.sha256()

    with open(file_path, 'rb') as file:
        while True:
            # Reading is buffered, so we can read smaller chunks.
            chunk = file.read(h.block_size)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()

def upload_file_udp(file_name: str, epoch: int, file_sufix: str, host: str, port: int):
    s = socket(AF_INET,SOCK_DGRAM)
    buf = 1024
    addr = (host,port)

    f=open(file_name + file_sufix,"rb")
    start_time = time.time()
    s.sendto(f"{file_name}{epoch}{file_sufix}".encode('utf-8'),addr)
    _ = s.recvfrom(1024)
    data = f.read(buf)
    while (data):
        if(s.sendto(data,addr)):
            data = f.read(buf)
    s.sendto(b"\r",addr)
    _ = s.recvfrom(1024)
    end_time = time.time()
    s.close()
    f.close()
    return end_time - start_time, get_digest(file_name + file_sufix)


if __name__ == "__main__":
    upload_file_udp(file_name="hd", file_sufix=".jpg", epoch=0)