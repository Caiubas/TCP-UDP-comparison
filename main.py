from datetime import datetime
from udpFileUpload import *
from tcpFileDownload import *
import pyshark
import hashlib
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np

load_dotenv()

def log_data(data_dict, filename="log.csv"):
    """
    Registra os dados de resultado em um .csv, incluindo dados estatísticos e timestamp da realização do teste.
    :param data_dict:
    :param filename:
    :return:
    """
    data_dict['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data_dict['desvio_padrao_tempo_udp'] = np.std(data_dict['times_udp'])
    data_dict['desvio_padrao_tempo_tcp'] = np.std(data_dict['times_tcp'])
    df = pd.DataFrame([data_dict])
    file_exists = os.path.exists(filename)
    df.to_csv(filename, mode='a', header=not file_exists, index=False)

def get_digest(file_path):
    """
    Calcula o hash do arquivo.
    :param file_path:
    :return:
    """
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
    """
    Deleta todos os arquivos no diretorio que comecem com "downloaded_".
    :param diretorio:
    :return:
    """
    for arquivo in os.listdir(diretorio):
        if arquivo.startswith("downloaded_"):
            caminho = os.path.join(diretorio, arquivo)
            if os.path.isfile(caminho):
                os.remove(caminho)

def print_results(results: dict):
    """
    Exibe os dados de results no terminal.
    :param results:
    :return:
    """
    print("file name: ", results['file_name'])
    print("file sufix: ", results['file_sufix'])
    print("file size: ", results['file_size'])
    print("times udp: ", results['times_udp'])
    print(f"total time upload udp: {results['total_time_upload_udp']}")
    print("times tcp: ", results['times_tcp'])
    print(f"total time download tcp: {results['total_time_download_tcp']}")
    print(f"crashes udp: {results['crashes_udp']}")
    print(f"crashes tcp: {results['crashes_tcp']}")
    print(f"udp corruption: {float(results['udp_corruption']):.3}%")
    print(f"corrupted bytes: {results['corrupted_bytes']}")
    print(f"tcp time outs: {results['tcp_time_outs']}")
    print(f"udp time outs: {results['udp_time_outs']}")


def compare_tcp_udp(epochs: int = 1, file_name: str = "small", file_sufix: str = ".jpg", host_ip: str = None, tcp_port: int = None, udp_port: int = None) -> dict:
    """
    Faz a comparação do protocolo de transporte tcp e udp.
    :param epochs:
    :param file_name:
    :param file_sufix:
    :param host_ip:
    :param tcp_port:
    :param udp_port:
    :return:
    """
    if host_ip is None:
        raise RuntimeError("host_ip must be provided as environment variable")

    if tcp_port is None or udp_port is None:
        raise RuntimeError("tcp_port and udp_port must be provided")

    times_udp = []
    times_tcp = []
    total_time_upload_udp = 0
    total_time_download_tcp = 0
    crashes_udp = 0
    crashes_tcp = 0
    original_hash = []
    hash_server = []
    hash_back = []
    udp_corruption = 0
    corrupted_bytes = []
    tcp_time_outs = 0
    udp_time_outs = 0


    print("UDP upload: ")
    for epoch in range(epochs):
        print(f"{(100*epoch / epochs):.4}%...", end="")
        try:
            new_time, hash = upload_file_udp(file_name=file_name, epoch=epoch, file_sufix=file_sufix, host=host_ip, port=udp_port)
        except Exception as e:
            print(e)
            udp_time_outs += 1
            epoch -= epochs
            continue
        original_hash.append(hash)
        total_time_upload_udp += new_time
        times_udp.append(new_time)

    print("\nTCP download: ")
    for epoch in range(epochs):
        print(f"{(100*epoch / epochs):.4}%...", end="")
        try:
            new_time, hash = download_file_tcp(file_name=file_name, epoch=epoch, file_sufix=file_sufix, host=host_ip, port=tcp_port)
        except Exception as e:
            print(e)
            udp_time_outs += 1
            epoch -= epochs
            continue
        hash_back.append(hash)
        total_time_download_tcp += new_time
        times_tcp.append(new_time)
    print("\n")

    response = "n"
    while not response.lower() == "y":
        print("proceed to download hashes?")
        response = input("y/n? ")

    for epoch in range(epochs):
        try:
            new_time, hash = download_file_tcp(file_name=file_name, epoch=epoch, file_sufix="_hash.txt", host=host_ip, port=tcp_port)
        except Exception as e:
            print(e)
            epoch -= epochs
            continue
        hash_server.append(hash)

    for epoch in range(epochs):
        if original_hash[epoch] != hash_server[epoch]:
            crashes_udp += 1
        if hash_server[epoch] != hash_back[epoch]:
            crashes_tcp += 1
        else:
            diffs, ratio = get_file_difference_ratio(file_name + file_sufix, "downloaded_" + file_name + f"{epoch}" + file_sufix)
            #print(f"Differences on file {epoch}: {diffs} bytes ({ratio:.2%} corrupted)")
            udp_corruption += ratio
            corrupted_bytes.append(diffs)

    udp_corruption = 100*udp_corruption/epochs

    with open(file_name + file_sufix, "rb") as f1:
        b1 = f1.read()
        file_size = len(b1)

    return {
        "epochs": epochs,
        "file_name": file_name,
        "file_sufix": file_sufix,
        "file_size": file_size,
        "total_time_upload_udp": total_time_upload_udp,
        "total_time_download_tcp": total_time_download_tcp,
        "times_udp": times_udp,
        "times_tcp": times_tcp,
        "crashes_udp": crashes_udp,
        "crashes_tcp": crashes_tcp,
        "udp_corruption": udp_corruption,
        "corrupted_bytes": corrupted_bytes,
        "tcp_time_outs": tcp_time_outs,
        "udp_time_outs": udp_time_outs,
    }





if __name__ == "__main__":
    epochs = 30
    file_name = "small"
    file_sufix = ".jpg"
    host_ip = os.getenv("HOST_IP")
    tcp_port = 8883
    udp_port = 8000
    file_names = ["small", "hd", "drum", "drum2"]
    file_suffixes = [".jpg", ".jpg", ".mp3", ".mp3"]

    for i in range(len(file_names)):
        delete_downloaded_files_on(".")
        results = compare_tcp_udp(epochs=epochs, file_name=file_names[i], file_sufix=file_suffixes[i], host_ip=host_ip, tcp_port=tcp_port, udp_port=udp_port)
        print_results(results)
        log_data(results)
        input("press enter to continue...")

    input("Press enter to continue and delete the downloaded files...")
    delete_downloaded_files_on(".")