import socket
import sys
from typing import Tuple
import signal

peerTable = []
#PeerTable.append({"ip": "192.168.56.10", "lnkport": 58001, "seqnumber": 1})
#PeerTable.append({"ip": "192.168.56.11", "lnkport": 58002, "seqnumber": 2})
addr: Tuple[str, int]

def processarComando(messageReceived: str, addr: Tuple[str, int]) -> str:
    global peerTable
    messageReceived = messageReceived.split(" ")
    comando = messageReceived[0]
    argumentos = messageReceived[1:]
    validos = ["REG", "UNR", "PEERS"]
    if comando not in validos:
        print("Comando invalido")
        return "NOK Comando invalido\n"
    
    if comando == "REG":
        if len(argumentos) != 1:
            print("Argumentos invalidos")
            return "NOK Argumentos invalidos\n"
        #receber REG lnkport e extrair porta (validar entre 1 e 65535);
        port = argumentos[0]
        if not port.isdigit() or int(port) < 1 or int(port) > 65535:
            print("Porta invalida")
            return "NOK Porta invalida\n"
        #verificar se o peer ja esta registrado e devolver o SQN registrado
        for peer in peerTable:
            if peer["ip"] == addr[0] and peer["lnkport"] == int(port):
                return "SQN "+ str(peer["seqnumber"]) + "\n"
        
        seqnumber = 1 if peerTable.__len__() == 0   else peerTable[peerTable.__len__()-1]["seqnumber"] + 1
        #registrar peer
        peerTable.append({"ip": addr[0], "lnkport": int(port), "seqnumber": seqnumber})
        print("Registrando para TCP", port, "com IP", addr[0], "SQN", seqnumber)
        return "SQN " + str(seqnumber) + "\n"
    if comando == "UNR":
        if len(argumentos) != 1:
            print("Argumentos invalidos")
            return "NOK Argumentos invalidos\n"
        #receber UNR nome e desregistrar
        seqnumber = argumentos[0]
        print("Desregistrando", seqnumber)
        for peer in peerTable:
            if peer["seqnumber"] == int(seqnumber):
                peerTable.remove(peer)
                return "OK\n"
        return "NOK Peer nao encontrado\n"
    
    if comando == "PEERS":
        if len(argumentos) != 0:
            print("Argumentos invalidos")
            return "NOK Argumentos invalidos\n"
        result: str = "LST\n"
        for peer in peerTable:
            result += f"{peer['ip']}:{peer['lnkport']}#{peer['seqnumber']}\n"
        # Não adicionar quebra de linha extra - o último peer já tem \n
        return result

def signal_handler(signum, frame):
    print("\nEncerrando servidor...")
    #guardar a tabela de peers em um arquivo
    with open("peerTable.txt", "w") as f:
        for peer in peerTable:
            f.write(f"{peer['ip']}:{peer['lnkport']}#{peer['seqnumber']}\n")
    sys.exit(0)

def carregarTabelaDePeers():
    global peerTable
    try:
        with open("peerTable.txt", "r") as f:
            for line in f:
                peerTable.append({"ip": line.split(":")[0], "lnkport": int(line.split(":")[1].split("#")[0]), "seqnumber": int(line.split("#")[1])})
    except FileNotFoundError:
        pass

def start_server():
    global peerTable
    carregarTabelaDePeers()
    #Capturar sinais de terminação (SIGINT/SIGTERM)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    port = sys.argv[1] if sys.argv.__len__() > 1 and sys.argv[1].isdigit() else 58000
    #lidar com o erro de porta ocupada
    try:
        soc.bind(("", port))
    except socket.error as e:
        print("Porta ocupada")
        sys.exit()
    print("Server UDP started on port", port)
    print("Ctrl+C para encerrar o servidor")
    soc.settimeout(1.0)  # 1 segundo
    while True:
        try:
            data, addr = soc.recvfrom(1024)
            messageReceived = data.decode().strip()
            message = processarComando(messageReceived, addr)
            soc.sendto(message.encode(), addr)
        except socket.timeout:
            continue

if __name__ == "__main__":
    start_server()