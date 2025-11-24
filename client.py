# -*- coding: utf-8 -*-
import socket
import sys
import select
from enum import Enum
from typing import List, Optional, Tuple

class NeighborAddResult(Enum):
    """Resultado da tentativa de adicionar um vizinho interno"""
    ACCEPT = "accept"                           # Aceite direto (há espaço)
    REJECT = "reject"                           # Rejeitado (seq maior que o próprio ou sem candidato a FRC)
    ACCEPT_WITH_REPLACEMENT = "accept_frc"      # Aceite via FRC (expulsar vizinho pior)
    ALREADY_NEIGHBOR = "already"                # Já é vizinho (evitar duplicados)

class Neighbor:
    def __init__(self, ip, port, seqnumber, socket_fd=None, status="pendente"):
        self.ip = ip
        self.port = port
        self.seqnumber = seqnumber
        self.socket_fd = socket_fd
        self.status = status

class Identifier:
    def __init__(self):
        self.identificadores = []
    
    def addIdentifier(self, identifier):
        self.identificadores.append(identifier)
    
    def removeIdentifier(self, identifier):
        self.identificadores.remove(identifier)
    
    def hasIdentifier(self, identifier):
        return identifier in self.identificadores
    
    def listIdentifiers(self):
        return self.identificadores

class Argumentos:
    def __init__(self):
        self.ipServer = "192.168.56.21"
        self.portServer = 58000
        self.lnkport = 8080
        self.neighMx = 5
        self.hopcount = 5

    def parse(self):
        switch = {
            "-s": "ipServer",
            "-p": "portServer",
            "-l": "lnkport",
            "-n": "neighMx",
            "-h": "hopcount"
        }
        for i in range(1, len(sys.argv)):
            if sys.argv[i] in switch:
                setattr(self, switch[sys.argv[i]], sys.argv[i + 1])
        
        # Garantir que são inteiros
        self.portServer = int(self.portServer)
        self.lnkport = int(self.lnkport)
        self.neighMx = int(self.neighMx)
        self.hopcount = int(self.hopcount)

class Peer:
    def __init__(self):
        self.internal_neighbors: List[Neighbor] = []
        self.external_neighbors: List[Neighbor] = []
        self.identifiers = Identifier()
        
        self.seqnumber = 0
        self.args = Argumentos()
        self.args.parse()
        self.client_socket_udp = None
        self.client_socket_tcp = None
        self.inputs = []
        self.outputs = []
        self.all_messages_to_send = {} # {"socketPeer": [message1, message2, ...]}

    
    def handle_cli_command(self,line):
        parts = line.strip().split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "join":
            self.handle_join(args)
        elif cmd == "leave":
            self.handle_leave(args)
        elif cmd == "show" and args and args[0] == "neighbors":
            self.handle_show_neighbors(args)
        elif cmd == "release" and args:
            self.handle_release(args)
        elif cmd == "post" and args:
            self.handle_post(args)
        elif cmd == "unpost" and args:
            self.handle_unpost(args)
        elif cmd == "list" and args and args[0] == "identifiers":
            self.handle_list_identifiers(args)
        elif cmd == "search" and args:
            self.handle_search(args)
        elif cmd == "exit":
            sys.exit(0)
        else:
            print("Comando não reconhecido")
    def handle_join(self,args):
        print("Comando JOIN recebido")
        # TODO: Implementar JOIN

    def handle_leave(self,args):
        print("Comando LEAVE recebido")
        # TODO: Implementar LEAVE

    def handle_show_neighbors(self,args):
        print("Comando SHOW NEIGHBORS recebido")
        # TODO: Implementar SHOW NEIGHBORS

    def handle_release(self,args):
        print("Comando RELEASE recebido")
        # TODO: Implementar RELEASE

    def handle_post(self,args):
        print("Comando POST recebido")
        # TODO: Implementar POST

    def handle_unpost(self,args):
        print("Comando UNPOST recebido")
        # TODO: Implementar UNPOST

    def handle_list_identifiers(self,args):
        print("Comando LIST IDENTIFIERS recebido")
        # TODO: Implementar LIST IDENTIFIERS

    def handle_search(self,args):
        print("Comando SEARCH recebido")
        print("Procurando pelo identificador", args[0])
        print("Procurando no proprio nó\n")
        if self.identifiers.hasIdentifier(args[0]):
            print("Identificador encontrado no proprio nó\n")
            return
        else:
            print("Identificador nao encontrado no proprio nó\n")
        print("Procurando nos vizinhos\n")
        #QRY identifier hopcount
        for neighbor in self.internal_neighbors:
            query = "QRY " + args[0] + " " + str(self.args.hopcount) + "\n"
            self.queue_tcp_message(neighbor.socket_fd, query)

    def send_udp_reg(self):
        message = "REG " + str(self.args.lnkport) + "\n"
        self.client_socket_udp.sendto(message.encode(), (self.args.ipServer, self.args.portServer))
    def send_udp_unr(self, seqnumber):
        message = "UNR " + str(seqnumber) + "\n"
        self.client_socket_udp.sendto(message.encode(), (self.args.ipServer, self.args.portServer))
    def send_udp_peers(self):
        message = "PEERS\n"
        self.client_socket_udp.sendto(message.encode(), (self.args.ipServer, self.args.portServer))
    def add_internal_neighbor(self, neigh: Neighbo, isFrc: bool=False) -> Tuple[NeighborAddResult, Optional[Neighbor]]:
        """
        Tenta adicionar um vizinho interno seguindo as regras do protocolo P2P.
        
        Regras:
        1. Se já existe como vizinho interno → ALREADY_NEIGHBOR
        2. Se há espaço livre → ACCEPT (aceita sem verificar seqnumber)
        3. Se tabela cheia:
           a. Se seq_incoming > seq_self → REJECT (não pode substituir)
           b. Se seq_incoming < seq_self → procurar candidato a FRC
              - Procurar vizinho com seq > seq_incoming
              - Se encontrar → ACCEPT_WITH_REPLACEMENT (expulsar vizinho pior)
              - Se não encontrar → REJECT
        
        Retorna:
            Tuple[NeighborAddResult, Optional[Neighbor]]: 
                - Resultado da operação
                - Vizinho expulso (se ACCEPT_WITH_REPLACEMENT) ou None
        """
        
        # 1. Verificar se já é vizinho interno (evitar duplicados)
        for existing in self.internal_neighbors:
            if existing.ip == neigh.ip and existing.port == neigh.port:
                return (NeighborAddResult.ALREADY_NEIGHBOR, None)
        
        # 2. Se há espaço livre, aceitar diretamente
        if len(self.internal_neighbors) < self.args.neighMx:
            self.internal_neighbors.append(neigh)
            neigh.status = "ativo"
            return (NeighborAddResult.ACCEPT, None)
        
        # 3. Tabela cheia - aplicar regras de seqnumber
        
        # 3a. Se seq_incoming > seq_self → rejeitar
        if neigh.seqnumber > self.seqnumber:
            return (NeighborAddResult.REJECT, None)
        
        if isFrc:
            # 3b. Se seq_incoming < seq_self → tentar FRC
            # Procurar vizinho interno com seq > seq_incoming (candidato a ser expulso)
            candidate_to_remove: Optional[Neighbor] = None
            
            for existing in self.internal_neighbors:
                if existing.seqnumber > neigh.seqnumber:
                    # Escolher o vizinho com maior seqnumber para expulsar
                    if candidate_to_remove is None or existing.seqnumber > candidate_to_remove.seqnumber:
                        candidate_to_remove = existing
            
            # Se não encontrou candidato, rejeitar
            if candidate_to_remove is None:
                return (NeighborAddResult.REJECT, None)
            
            # Expulsar o vizinho pior e adicionar o novo
            self.internal_neighbors.remove(candidate_to_remove)
            self.internal_neighbors.append(neigh)
            neigh.status = "ativo"
            candidate_to_remove.status = "expulso"
            
            return (NeighborAddResult.ACCEPT_WITH_REPLACEMENT, candidate_to_remove)

    def add_external_neighbor(self, neigh: Neighbor):
        """Adiciona um vizinho externo (sem verificações de seqnumber)"""
        # Verificar se já existe
        for existing in self.external_neighbors:
            if existing.ip == neigh.ip and existing.port == neigh.port:
                return
        
        self.external_neighbors.append(neigh)
        neigh.status = "ativo"

    def remove_neighbor_by_seq(self, seqnumber: int) -> Optional[Neighbor]:
        """Remove um vizinho pelo seqnumber e retorna-o se encontrado"""
        for neighbor in self.internal_neighbors:
            if neighbor.seqnumber == seqnumber:
                self.internal_neighbors.remove(neighbor)
                return neighbor
        
        for neighbor in self.external_neighbors:
            if neighbor.seqnumber == seqnumber:
                self.external_neighbors.remove(neighbor)
                return neighbor
        
        return None

    def setSeqnumber(self, seqnumber: int):
        """Define o seqnumber do peer"""
        self.seqnumber = seqnumber

    def getSeqnumber(self) -> int:
        """Retorna o seqnumber do peer"""
        return self.seqnumber

    def process_command(self, command: str):
        """Processa comandos CLI"""
        print(f"Processando comando: {command.strip()}")
        # TODO: Implementar lógica de comandos CLI aqui

    def handle_udp_response(self, message: str):
        """Processa respostas UDP do servidor (SQN, LST, OK, NOK)"""
        print(f"[UDP Server] {message.strip()}")
        # TODO: Implementar parsing de SQN, LST, OK, NOK
    
    def handle_tcp_query_message(self, args: list[str]):
        """Processa mensagens TCP de query"""
        print(f"[TCP Query] {args}")
        identifier = args[0]
        hopcount = int(args[1])
        if hopcount > 0 and self.identifiers.hasIdentifier(identifier):
            print("Identificador encontrado no proprio nó\n")
            self.queue_tcp_message(neighbor.socket_fd, "FND " + identifier + "\n")
            return
        elif hopcount > 1:
            print("Identificador nao encontrado no proprio nó\n")
            print("Procurando nos vizinhos\n")
            #QRY identifier hopcount
            for neighbor in self.internal_neighbors:
                query = "QRY " + args[0] + " " + str(hopcount - 1) + "\n"
                self.queue_tcp_message(neighbor.socket_fd, query)
        else:
            print("Identificador nao encontrado no proprio nó\n")
            self.queue_tcp_message(neighbor.socket_fd, "NOTFND " + identifier + "\n")

    def handle_tcp_peer_message(self, message: str):
        """Processa mensagens TCP recebidas de outros peers (LNK, FRC, QUERY, etc)"""
        print(f"[TCP Peer] {message.strip()}")
        parts = message.strip().split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]
        if cmd == "QRY":
            self.handle_tcp_query_message(args)    
        else:
            print("Comando TCP não reconhecido")
        # TODO: Implementar parsing de LNK, FRC, CONTENT, etc

    def accept_incoming_connection(self, server_socket):
        """Aceita uma nova conexão TCP de entrada e cria um vizinho"""
        try:
            conn, addr = server_socket.accept()
            print(f"[TCP] Nova conexão de {addr}")
            conn.setblocking(False)
            self.inputs.append(conn)
            self.all_messages_to_send[conn] = []  # Inicializa fila de mensagens
            # TODO: Aguardar mensagem LNK antes de adicionar como vizinho
            # self.add_internal_neighbor(Neighbor(addr[0], addr[1], seqnumber_from_lnk))
        except Exception as e:
            print(f"Erro ao aceitar conexão: {e}")
        
    def queue_tcp_message(self, peer_socket, message):
        """Adiciona uma mensagem à fila de envio TCP para um peer específico"""
        try:
            if peer_socket not in self.all_messages_to_send:
                self.all_messages_to_send[peer_socket] = []
            self.all_messages_to_send[peer_socket].append(message)
            # Adicionar socket aos outputs para que select() detecte quando pode escrever
            if peer_socket not in self.outputs:
                self.outputs.append(peer_socket)
        except Exception as e:
            print(f"Erro ao adicionar mensagem à fila: {e}")
    
    def flush_tcp_queue(self, peer_socket):
        """Envia a próxima mensagem da fila TCP para o peer (chamado quando socket está pronto)"""
        try:
            if peer_socket in self.all_messages_to_send and len(self.all_messages_to_send[peer_socket]) > 0:
                message = self.all_messages_to_send[peer_socket].pop(0)
                peer_socket.send(message.encode())
                # Se não há mais mensagens, remover dos outputs
                if len(self.all_messages_to_send[peer_socket]) == 0:
                    if peer_socket in self.outputs:
                        self.outputs.remove(peer_socket)
        except Exception as e:
            print(f"Erro ao enviar mensagem TCP: {e}")

    def start_server_loop(self):
        """Inicia o loop principal do servidor TCP"""
        print(f"Iniciando Peer na porta {self.args.lnkport}...")
        self.client_socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client_socket_tcp.bind(("", self.args.lnkport))
        self.client_socket_tcp.listen(self.args.neighMx * 2)
        self.client_socket_tcp.setblocking(False)
        self.client_socket_udp.setblocking(False) 

        self.inputs = [self.client_socket_tcp,self.client_socket_udp, sys.stdin]
        self.outputs = [self.client_socket_udp]

        # Imprime prompt antes do loop
        print("> ", end="", flush=True) 
        while True:
            readable, writable, exceptional = select.select(self.inputs, self.outputs, self.inputs)
            
            for s in readable:
                if s is self.client_socket_tcp:
                    if len(self.internal_neighbors) + len(self.external_neighbors) >= self.args.neighMx:
                        print("Limite de vizinhos atingido")
                        # Poderia aceitar e fechar para ser educado, mas continue por enquanto
                        continue
                    self.accept_incoming_connection(s)
                elif s is self.client_socket_udp:
                    data, addr = s.recvfrom(1024)
                    self.handle_udp_response(data.decode())

                elif s is sys.stdin:
                    data = s.readline()
                    self.handle_cli_command(data)
                    print("> ", end="", flush=True) 
                    
                else:
                    try:
                        data = s.recv(1024)
                        if data:
                            self.handle_tcp_peer_message(data.decode())
                        else:
                            print("Desconectado")
                            self.inputs.remove(s)
                            if s in self.outputs:
                                self.outputs.remove(s)
                            s.close()
                    except Exception as e:
                        print(f"Erro no socket: {e}")
                        if s in self.inputs:
                            self.inputs.remove(s)
                        if s in self.outputs:
                            self.outputs.remove(s)
                        s.close()

            for s in writable:
                # Enviar mensagens TCP enfileiradas para peers
                if s not in [self.client_socket_tcp, self.client_socket_udp, sys.stdin]:
                    self.flush_tcp_queue(s)
            for s in exceptional:
                print("Exceção no socket")
                if s in self.inputs:
                    self.inputs.remove(s)
                if s in self.outputs:
                    self.outputs.remove(s)
                s.close()


if __name__ == "__main__":
    peer = Peer()
    peer.start_server_loop()