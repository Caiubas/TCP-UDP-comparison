import subprocess
import time
import socket
import hashlib
import os

def get_digest(file_path):
    h = hashlib.sha256()
    with open(file_path, 'rb') as file:
        while chunk := file.read(h.block_size):
            h.update(chunk)
    return h.hexdigest()

def download_file_tcp(file_name: str, epoch: int, file_sufix: str, host: str, port: int):
    s = socket.socket()
    start_time = time.time()
    s.connect((host, port))
    download_file = file_name + f"{epoch}" + file_sufix
    s.send(download_file.encode('utf-8'))
    file_name_dl = "downloaded_" + download_file

    with open(file_name_dl, 'wb') as f:
        while True:
            data = s.recv(1024)
            if not data:
                break
            f.write(data)

    s.close()
    end_time = time.time()

    if not file_name_dl.endswith(".txt"):
        return end_time - start_time, get_digest(file_name_dl)

    with open(file_name_dl, "rb") as f:
        return end_time - start_time, f.read().decode('utf-8')



if __name__ == "__main__":
    download_file_tcp(file_name="hd", epoch=0, file_sufix=".jpg")