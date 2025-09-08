from udpFileUpload import *
from tcpFileDownload import *
import pyshark
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

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

def get_file_difference_ratio(file1, file2):
    with open(file1, "rb") as f1, open(file2, "rb") as f2:
        b1, b2 = f1.read(), f2.read()
    length = min(len(b1), len(b2))
    diffs = sum(c1 != c2 for c1, c2 in zip(b1[:length], b2[:length]))
    diffs += abs(len(b1) - len(b2))  # account for length difference
    return diffs, diffs / max(len(b1), len(b2))

def delete_downloaded_files_on(diretorio):
    for arquivo in os.listdir(diretorio):
        if arquivo.startswith("downloaded_"):
            caminho = os.path.join(diretorio, arquivo)
            if os.path.isfile(caminho):
                os.remove(caminho)

def compare_tcp_udp(epochs: int = 1, file_name: str = "small", file_sufix: str = ".jpg", host_ip: str = None, tcp_port: int = None, udp_port: int = None) -> dict:

    if host_ip is None:
        raise RuntimeError("host_ip must be provided as environment variable")

    if tcp_port is None or udp_port is None:
        raise RuntimeError("tcp_port and udp_port must be provided")

    time_upload_udp = 0
    time_download_tcp = 0
    crashes_udp = 0
    crashes_tcp = 0
    original_hash = []
    hash_server = []
    hash_back = []
    udp_corruption = 0

    print("UDP upload: ")
    for epoch in range(epochs):
        print(f"{100*epoch / epochs}%...", end="")
        new_time, hash = upload_file_udp(file_name=file_name, epoch=epoch, file_sufix=file_sufix, host=host_ip, port=udp_port)
        original_hash.append(hash)
        time_upload_udp += new_time

    print("\nTCP download: ")
    for epoch in range(epochs):
        print(f"{100*epoch / epochs}%...", end="")
        new_time, hash = download_file_tcp(file_name=file_name, epoch=epoch, file_sufix=file_sufix, host=host_ip, port=tcp_port)
        hash_back.append(hash)
        time_download_tcp += new_time
    print("\n")

    response = "n"
    while not response.lower() == "y":
        print("proceed to download hashes?")
        response = input("y/n? ")

    for epoch in range(epochs):
        new_time, hash = download_file_tcp(file_name=file_name, epoch=epoch, file_sufix="_hash.txt", host=host_ip, port=tcp_port)
        hash_server.append(hash)

    for epoch in range(epochs):
        if original_hash[epoch] != hash_server[epoch]:
            crashes_udp += 1
        if hash_server[epoch] != hash_back[epoch]:
            crashes_tcp += 1
        else:
            diffs, ratio = get_file_difference_ratio(file_name + file_sufix, "downloaded_" + file_name + f"{epoch}" + file_sufix)
            print(f"Differences on file {epoch}: {diffs} bytes ({ratio:.2%} corrupted)")
            udp_corruption += ratio

    udp_corruption = 100*udp_corruption/epochs
    return {
        "time_upload_udp": time_upload_udp,
        "time_download_tcp": time_download_tcp,
        "crashes_udp": crashes_udp,
        "crashes_tcp": crashes_tcp,
        "udp_corruption": udp_corruption
    }

if __name__ == "__main__":
    epochs = 20
    file_name = "hd"
    file_sufix = ".jpg"
    host_ip = os.getenv("HOST_IP")
    tcp_port = 8883
    udp_port = 8000

    delete_downloaded_files_on(".")
    results = compare_tcp_udp(epochs=epochs, file_name=file_name, file_sufix=file_sufix, host_ip=host_ip, tcp_port=tcp_port, udp_port=udp_port)

    print(f"epochs: {epochs}")
    print(f"crashes udp: {results['crashes_udp']}")
    print(f"crashes tcp: {results['crashes_tcp']}")
    print(f"time upload udp: {results['time_upload_udp']/epochs}")
    print(f"time download tcp: {results['time_download_tcp']/epochs}")
    print(f"udp corruption: {float(results['udp_corruption']):.3}%")

    input("Press enter to continue and delete the downloaded files...")
    delete_downloaded_files_on(".")