import socket
import sys
import select
from typing import List, Optional, Tuple
from logic import transport
from common.models import Neighbor, NeighborAddResult, Identifier, QueryState
from common.args import Argumentos
from logic import network, neighbor_manager, transport
from cli import interface
import time

class Peer:
    def __init__(self):
        self.internal_neighbors: List[Neighbor] = []
        self.external_neighbors: List[Neighbor] = []
        self.identifiers = Identifier()
        self.eligible_peers: List[Tuple[str, int, int]] = []
        self.seqnumber = 0
        self.args = Argumentos()
        self.args.parse()
        self.client_socket_udp = None
        self.client_socket_tcp = None
        self.server_socket_tcp = None
        self.inputs = []
        self.outputs = []
        self.active_queries = {} # {identifier: QueryState}
        self.all_messages_to_send = {} # {"socketPeer": [message1, message2, ...]}
        self.frc_used_in_recovery = False
        self.query_timeouts = {}
        self.last_query_cleanup = 0
        # Controle de recuperação de vizinhos externos (para evitar loops)
        self.last_external_peers_request = 0
        self.external_recovery_min_interval = 5  # segundos entre pedidos PEERS
        self.external_recovery_attempts = 0
        self.max_external_recovery_attempts = 3
        # Controle de candidatos falhados (backoff temporário em candidates de LST)
        self.failed_candidates = {}  # {(ip,port,seq): timestamp}
        self.failed_candidate_ttl = 30  # segundos para manter como falhado

    def handle_cli_command(self, line):
        interface.handle_cli_command(self, line)

    def handle_udp_response(self, message):
        network.handle_udp_response(self, message)

    def handle_tcp_peer_message(self, message, socketPeer):
        network.handle_tcp_peer_message(self, message, socketPeer)

    def send_udp_reg(self):
        transport.send_udp_reg(self)

    def send_udp_unr(self, seqnumber):
        transport.send_udp_unr(self, seqnumber)

    def send_udp_peers(self):
        transport.send_udp_peers(self)

    def add_internal_neighbor(self, neigh: Neighbor, isFrc: bool=False) -> Tuple[NeighborAddResult, Optional[Neighbor]]:
        return neighbor_manager.add_internal_neighbor(self, neigh, isFrc)

    def add_external_neighbor(self, neigh: Neighbor):
        neighbor_manager.add_external_neighbor(self, neigh)
        # Ao obter pelo menos um vizinho externo, resetar tentativas de recuperação
        if self.external_neighbors:
            self.external_recovery_attempts = 0
            # Se este peer estava com falhas marcadas, remover do mapa
            key = (neigh.ip, neigh.port, neigh.seqnumber)
            if key in self.failed_candidates:
                del self.failed_candidates[key]

    def remove_neighbor_by_seq(self, seqnumber: int) -> Optional[Neighbor]:
        return neighbor_manager.remove_neighbor_by_seq(self, seqnumber)

    def setSeqnumber(self, seqnumber: int):
        """Define o seqnumber do peer"""
        self.seqnumber = seqnumber

    def getSeqnumber(self) -> int:
        """Retorna o seqnumber do peer"""
        return self.seqnumber

    def accept_incoming_connection(self, server_socket):
        transport.accept_incoming_connection(self, server_socket)
        
    def queue_tcp_message(self, peer_socket, message):
        transport.queue_tcp_message(self, peer_socket, message)
    
    def flush_tcp_queue(self, peer_socket):
        transport.flush_tcp_queue(self, peer_socket)
    
    def cleanup_expired_queries(self):
        """Remove queries que expiraram (sem respostas por muito tempo)"""
        import time
        current_time = time.time()
        query_timeout = 30  # 30 segundos
        
        # Limpar a cada 5 segundos
        if current_time - self.last_query_cleanup < 5:
            return
        
        self.last_query_cleanup = current_time
        expired_queries = []
        
        for identifier, timestamp in list(self.query_timeouts.items()):
            if current_time - timestamp > query_timeout:
                expired_queries.append(identifier)
        
        for identifier in expired_queries:
            if identifier in self.active_queries:
                query_state = self.active_queries[identifier]
                if query_state.requester_socket:
                    self.queue_tcp_message(query_state.requester_socket, f"NOTFND {identifier}\n")
                print(f"[Query] Query {identifier} expirada (timeout)")
                del self.active_queries[identifier]
            del self.query_timeouts[identifier]

    def handle_disconnection(self, socket_peer):
        """Lida com a desconexão de um peer"""
        
        # Remover vizinho da lista
        removed_neighbor = None
        for neighbor in self.internal_neighbors:
            if neighbor.socket_fd == socket_peer:
                self.internal_neighbors.remove(neighbor)
                removed_neighbor = neighbor
                print(f"[Disconnect] Vizinho interno removido: seq={neighbor.seqnumber}")
                break
        
        if not removed_neighbor:
            for neighbor in self.external_neighbors:
                if neighbor.socket_fd == socket_peer:
                    self.external_neighbors.remove(neighbor)
                    removed_neighbor = neighbor
                    print(f"[Disconnect] Vizinho externo removido: {neighbor.ip}:{neighbor.port}")
                    break
        
        # Tratamento de queries ativas: decrementar pending_count para queries onde este vizinho estava envolvido
        queries_to_remove = []
        for identifier, query_state in self.active_queries.items():
            if query_state.requester_socket != socket_peer:  # Se não foi o requester que desconectou
                # Este vizinho estava em pending, então decrementar
                query_state.pending_count -= 1
                if query_state.pending_count <= 0:
                    queries_to_remove.append(identifier)
        
        # Remover queries sem respostas pendentes
        for identifier in queries_to_remove:
            if identifier in self.active_queries:
                query_state = self.active_queries[identifier]
                if query_state.requester_socket:
                    self.queue_tcp_message(query_state.requester_socket, f"NOTFND {identifier}\n")
                del self.active_queries[identifier]
        
        # Limpar socket
        if socket_peer in self.inputs:
            self.inputs.remove(socket_peer)
        if socket_peer in self.outputs:
            self.outputs.remove(socket_peer)
        socket_peer.close()
        
        # Verificar se ficamos sem vizinhos externos
        if not self.external_neighbors:
            now = time.time()
            if self.external_recovery_attempts >= self.max_external_recovery_attempts:
                print("[Disconnect] Limite de tentativas de recuperação atingido. Aguardando conexões de entrada.")
            elif now - self.last_external_peers_request < self.external_recovery_min_interval:
                print("[Disconnect] Pedido PEERS já enviado recentemente. Aguardando resposta.")
            else:
                print("[Disconnect] Sem vizinhos externos! Solicitando lista de peers...")
                self.frc_used_in_recovery = False  # Reset FRC para próxima recuperação
                self.send_udp_peers()
                self.last_external_peers_request = now
                self.external_recovery_attempts += 1
                # A lógica de reconexão continuará no handler de LST

    def start_server_loop(self):
        """Inicia o loop principal do servidor TCP"""
        print(f"Iniciando Peer na porta {self.args.lnkport}...")
        self.client_socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client_socket_tcp.bind(("", self.args.lnkport))
        self.client_socket_tcp.listen(self.args.neighMx * 2)
        self.client_socket_tcp.setblocking(False)
        self.client_socket_udp.setblocking(False) 
        self.server_socket_tcp.setblocking(False)

        self.inputs = [self.client_socket_tcp,self.client_socket_udp, sys.stdin]
        self.outputs = [self.client_socket_udp]

        # Imprime prompt antes do loop
        print("> ", end="", flush=True) 
        while True:
            # Limpeza de queries expiradas
            self.cleanup_expired_queries()
            
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
                            self.handle_tcp_peer_message(data.decode(), s)
                        else:
                            # Desconexão detectada
                            print("Desconectado")
                            self.handle_disconnection(s)
                    except Exception as e:
                        print(f"Erro no socket: {e}")
                        self.handle_disconnection(s)

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
