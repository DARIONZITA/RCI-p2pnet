import socket
from common.models import Neighbor

def send_udp_reg(peer):
    message = "REG " + str(peer.args.lnkport) + "\n"
    peer.client_socket_udp.sendto(message.encode(), (peer.args.ipServer, peer.args.portServer))

def send_udp_unr(peer, seqnumber):
    message = "UNR " + str(seqnumber) + "\n"
    peer.client_socket_udp.sendto(message.encode(), (peer.args.ipServer, peer.args.portServer))

def send_udp_peers(peer):
    message = "PEERS\n"
    peer.client_socket_udp.sendto(message.encode(), (peer.args.ipServer, peer.args.portServer))

def queue_tcp_message(peer, peer_socket, message):
    """Adiciona uma mensagem à fila de envio TCP para um peer específico"""
    try:
        if peer_socket not in peer.all_messages_to_send:
            peer.all_messages_to_send[peer_socket] = []
        peer.all_messages_to_send[peer_socket].append(message)
        # Adicionar socket aos outputs para que select() detecte quando pode escrever
        if peer_socket not in peer.outputs:
            peer.outputs.append(peer_socket)
    except Exception as e:
        print(f"Erro ao adicionar mensagem à fila: {e}")

def flush_tcp_queue(peer, peer_socket):
    """Envia a próxima mensagem da fila TCP para o peer (chamado quando socket está pronto)"""
    try:
        if peer_socket in peer.all_messages_to_send and len(peer.all_messages_to_send[peer_socket]) > 0:
            message = peer.all_messages_to_send[peer_socket].pop(0)
            peer_socket.send(message.encode())
            # Se não há mais mensagens, remover dos outputs
            if len(peer.all_messages_to_send[peer_socket]) == 0:
                if peer_socket in peer.outputs:
                    peer.outputs.remove(peer_socket)
    except Exception as e:
        print(f"Erro ao enviar mensagem TCP: {e}")

def accept_incoming_connection(peer, server_socket):
    """Aceita uma nova conexão TCP de entrada e cria um vizinho"""
    try:
        conn, addr = server_socket.accept()
        print(f"[TCP] Nova conexão de {addr}")
        conn.setblocking(False)
        peer.inputs.append(conn)
        peer.all_messages_to_send[conn] = []  # Inicializa fila de mensagens
        # Aguardar mensagem LNK/FRC antes de adicionar como vizinho
    except Exception as e:
        print(f"Erro ao aceitar conexão: {e}")

def connect_to_peer(peer, ip, port, seq, use_frc=False):
    """Conecta a um peer externo e envia LNK ou FRC"""
    try:
        # Validar limite de vizinhos externos
        if len(peer.external_neighbors) >= peer.args.neighMx:
            print(f"[Connect] Limite de vizinhos externos atingido ({peer.args.neighMx})")
            return None
        
        # Detecção de conexões duplicadas
        for existing in peer.external_neighbors:
            if existing.ip == ip and existing.port == port:
                print(f"[Connect] Já existe conexão pendente com {ip}:{port}")
                return None
        
        for existing in peer.internal_neighbors:
            if existing.ip == ip and existing.port == port:
                print(f"[Connect] Já existe conexão ativa com {ip}:{port}")
                return None
        
        # Criar novo socket para cada conexão
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_socket.setblocking(False)
        
        # Tentar conectar (non-blocking)
        try:
            new_socket.connect((ip, port))
        except BlockingIOError:
            # Normal para non-blocking socket
            pass
        except Exception as e:
            print(f"[Connect] Erro ao conectar a {ip}:{port}: {e}")
            new_socket.close()
            return None
        
        # Adicionar aos inputs e outputs
        peer.inputs.append(new_socket)
        peer.all_messages_to_send[new_socket] = []
        
        # Enviar LNK ou FRC
        if use_frc:
            message = f"FRC {peer.getSeqnumber()}\n"
            print(f"[Connect] Enviando FRC para {ip}:{port}")
        else:
            message = f"LNK {peer.getSeqnumber()}\n"
            print(f"[Connect] Enviando LNK para {ip}:{port}")
        
        queue_tcp_message(peer, new_socket, message)
        
        # Criar objeto Neighbor (status pendente até receber CNF)
        neigh = Neighbor(ip, port, seq, new_socket, "pendente")  # seqnumber será atualizado depois
        peer.add_external_neighbor(neigh)
        
        return new_socket
        
    except Exception as e:
        print(f"[Connect] Erro ao conectar a {ip}:{port}: {e}")
        return None
