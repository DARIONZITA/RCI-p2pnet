from logic import neighbor_manager
from common.models import Neighbor, NeighborAddResult
from common.models import QueryState
from logic import transport
from typing import List
import time

def handle_udp_response(peer, message: str):
    """Processa respostas UDP do servidor (SQN, LST, OK, NOK)"""
   
    
    print(f"[UDP Server] {message.strip()}")
    parts = message.strip().split()
    
    if not parts:
        return
    
    cmd = parts[0].upper()
    
    if cmd == "SQN":
        # SQN seqnumber - Servidor atribuiu número de sequência
        if len(parts) < 2:
            print("[UDP] Erro: SQN sem seqnumber")
            return
        
        seqnumber = int(parts[1])
        peer.setSeqnumber(seqnumber)
        print(f"[UDP] Seqnumber atribuído: {seqnumber}")
        
    elif cmd == "LST":
        # LST\n ip:port#seqnumber\n ip:port#seqnumber\n
        print(f"[UDP] Lista de peers recebida")
        
        if len(parts) < 1:
            print("[UDP] Nenhum peer na lista")
            return
        
        # Parsear lista de peers
        peers_list = []
        for peer_info in parts[1:]:
            if not peer_info.strip():  # Ignorar strings vazias
                continue
            try:
                ip, port = peer_info.split("#")[0].split(":")
                seq = peer_info.split("#")[1]
                peers_list.append((ip, int(port), int(seq)))
            except:
                print(f"[UDP] Erro ao parsear peer: {peer_info}")
        
        # Filtrar peers com seqnumber inferior ao nosso
        eligible_peers = [(ip, port, seq) for ip, port, seq in peers_list 
                          if seq < peer.getSeqnumber() and port != peer.args.lnkport]
        
        if not eligible_peers:
            print("[UDP] Nenhum peer elegível para conexão")
            if peer.internal_neighbors:
                print("[AVISO] A rede pode estar desconexa!")
            return
        
        # Calcular quantos vizinhos externos podemos ter
        max_external = peer.args.neighMx - len(peer.internal_neighbors)
        current_external = len(peer.external_neighbors)
        needed = max_external - current_external
        
        if needed <= 0:
            print("[UDP] Já temos vizinhos externos suficientes")
            return
        
        # Ordenar por seqnumber (preferir menores)
        eligible_peers.sort(key=lambda x: x[2])
        peer.eligible_peers += eligible_peers
        print(f"[UDP] Vizinhos elegíveis para conexão: {peer.eligible_peers}")
        
        # Conectar aos peers elegíveis - usar FRC apenas uma vez durante recovery
        frc_used = False
        for i, (ip, port, seq) in enumerate(eligible_peers[:needed]):
            print(f"[UDP] Tentando conectar a {ip}:{port} (seq={seq})")
            # Usar FRC apenas uma vez se em modo recovery e não temos vizinhos externos
            use_frc = (not peer.external_neighbors and not frc_used and not peer.frc_used_in_recovery)
            if use_frc:
                print(f"[UDP] Usando FRC para {ip}:{port} (primeira tentativa de recovery)")
                peer.frc_used_in_recovery = True
                frc_used = True
            transport.connect_to_peer(peer, ip, port, seq, use_frc=use_frc)
        
    elif cmd == "OK":
        print("[UDP] Operação confirmada pelo servidor")
        
    elif cmd == "NOK":
        print("[UDP] Operação rejeitada pelo servidor")
    
    else:
        print(f"[UDP] Comando desconhecido: {cmd}")


def handle_tcp_link_message(peer, args: List[str], socketPeer, is_frc=False):
    """Processa mensagens TCP de ligação (LNK ou FRC)"""
    remote_ip, remote_port = socketPeer.getpeername()
    print(f"[TCP {'FRC' if is_frc else 'LNK'}] {args} in ip/port {remote_ip}:{remote_port}")
    
    if len(args) < 1:
        print(f"[TCP] Erro: comando sem seqnumber")
        socketPeer.close()
        return
    
    try:
        peer_seqnumber = int(args[0])
    except ValueError:
        print(f"[TCP] Erro: seqnumber inválido")
        socketPeer.close()
        return
    
    # Validar que peer_seqnumber < meu_seqnumber (regra do protocolo)
    if peer_seqnumber >= peer.getSeqnumber():
        print(f"[TCP] Rejeição: seqnumber {peer_seqnumber} >= meu seqnumber {peer.getSeqnumber()}")
        socketPeer.close()
        return
    
    # Validar limite de vizinhos internos (exceto para FRC temporário)
    if len(peer.internal_neighbors) >= peer.args.neighMx and not is_frc:
        print(f"[TCP] Limite de vizinhos internos atingido ({peer.args.neighMx})")
        socketPeer.close()
        return
    
    # Criar objeto Neighbor
    neigh = Neighbor(remote_ip, remote_port, peer_seqnumber, socketPeer, "pendente")
    
    # Tentar adicionar como vizinho interno
    result, replaced_neighbor = peer.add_internal_neighbor(neigh, isFrc=is_frc)
    
    if result == NeighborAddResult.ACCEPT or result == NeighborAddResult.ACCEPT_WITH_REPLACEMENT:
        # Confirmar conexão
        peer.queue_tcp_message(socketPeer, "CNF\n")
        neigh.status = "ativo"
        print(f"[TCP] Conexão aceita de {remote_ip}:{remote_port}")
        
        if result == NeighborAddResult.ACCEPT_WITH_REPLACEMENT and replaced_neighbor:
            # Fechar conexão com vizinho substituído
            if replaced_neighbor.socket_fd:
                print(f"[TCP] Fechando conexão com vizinho substituído {replaced_neighbor.ip}:{replaced_neighbor.port}")
                peer.handle_disconnection(replaced_neighbor.socket_fd)
    else:
        # Rejeitar conexão
        print(f"[TCP] Rejeição: resultado {result}")
        socketPeer.close()


def handle_tcp_query_message(peer, args: List[str], socketPeer):
    """Processa mensagens TCP de query"""
    remote_ip, remote_port = socketPeer.getpeername()
    print(f"[TCP Query] {args} in ip/port {remote_ip}:{remote_port}")
    identifier = args[0]
    hopcount = int(args[1])
    
    # 1. Verificar se tenho o recurso
    if peer.identifiers.hasIdentifier(identifier):
        print("Identificador encontrado no proprio nó\n")
        peer.queue_tcp_message(socketPeer, "FND " + identifier + "\n")
        return

    # 2. Se hopcount > 0, propagar para vizinhos
    if hopcount > 0:
        print("Identificador nao encontrado no proprio nó\n")
        print("Procurando nos vizinhos\n")
        
        # Filtrar vizinhos para não enviar de volta para quem pediu (split horizon simples)
        # Nota: socketPeer é quem pediu.
        neighbors_to_query = [n for n in peer.internal_neighbors if n.socket_fd != socketPeer]
        neighbors_to_query += [n for n in peer.external_neighbors if n.socket_fd != socketPeer]
        
        if not neighbors_to_query:
            # Se não há vizinhos para perguntar, responder NOTFND imediatamente
            peer.queue_tcp_message(socketPeer, "NOTFND " + identifier + "\n")
            return

        # Criar estado da query
        peer.active_queries[identifier] = QueryState(socketPeer, identifier, len(neighbors_to_query))
        peer.query_timeouts[identifier] = time.time()  # Marcar tempo de criação para timeout
        
        # Enviar QRY para vizinhos
        query = "QRY " + identifier + " " + str(hopcount - 1) + "\n"
        for neighbor in neighbors_to_query:
            peer.queue_tcp_message(neighbor.socket_fd, query)
            
    else:
        # 3. TTL expirou e não tenho o recurso
        print("Identificador nao encontrado no proprio nó (TTL expirou)\n")
        peer.queue_tcp_message(socketPeer, "NOTFND " + identifier + "\n")

def handle_tcp_notfnd_message(peer, args: List[str], socketPeer):
    """Processa mensagens TCP de nao encontrado"""
    remote_ip, remote_port = socketPeer.getpeername()
    print(f"[TCP NotFound] {args} in ip/port {remote_ip}:{remote_port}")
    identifier = args[0]
    
    if identifier in peer.active_queries:
        query_state = peer.active_queries[identifier]
        query_state.pending_count -= 1
        
        # Se todos os vizinhos responderam NOTFND
        if query_state.pending_count == 0:
            if query_state.requester_socket is None:
                # Query local
                print(f"Identificador {identifier} não encontrado (NOTFND recebido de todos)")
            else:
                # Encaminhar para o requester original
                peer.queue_tcp_message(query_state.requester_socket, "NOTFND " + identifier + "\n")
            
            del peer.active_queries[identifier]

def handle_tcp_fnd_message(peer, args: List[str], socketPeer):
    """Processa mensagens TCP de encontrado"""
    remote_ip, remote_port = socketPeer.getpeername()
    print(f"[TCP Found] {args} in ip/port {remote_ip}:{remote_port}")
    identifier = args[0]
    
    if identifier in peer.active_queries:
        query_state = peer.active_queries[identifier]
        
        if query_state.requester_socket is None:
            # Query local
            print(f"Identificador {identifier} encontrado!")
        else:
            # Encontrou! Encaminhar imediatamente para o requester
            peer.queue_tcp_message(query_state.requester_socket, "FND " + identifier + "\n")
        peer.identifiers.addIdentifier(identifier)  # Adicionar ao meu conjunto de identificadores
        
        # Limpar estado (não precisamos esperar pelos outros)
        del peer.active_queries[identifier]

def handle_tcp_lnk_message(peer, args: List[str], socketPeer):
    """Processa mensagem LNK (pedido de ligação)"""

    
    if not args:
        print("[LNK] Erro: seqnumber não fornecido")
        socketPeer.close()
        return
    
    remote_seqnumber = int(args[0])
    remote_ip, remote_port = socketPeer.getpeername()
    print(f"[LNK] Pedido de ligação de {remote_ip}:{remote_port} (seq={remote_seqnumber})")
    
    # Criar objeto Neighbor
    neigh = Neighbor(remote_ip, remote_port, remote_seqnumber, socketPeer, "pendente")
    
    # Tentar adicionar como vizinho interno
    result, removed_neighbor = peer.add_internal_neighbor(neigh, isFrc=False)
    
    if result == neighbor_manager.NeighborAddResult.ACCEPT or result == neighbor_manager.NeighborAddResult.ALREADY_NEIGHBOR:
        # Aceitar ligação
        print(f"[LNK] Ligação aceite com {remote_ip}:{remote_port}")
        peer.queue_tcp_message(socketPeer, "CNF\n")
    else:
        # Rejeitar ligação (fechar socket)
        print(f"[LNK] Ligação rejeitada com {remote_ip}:{remote_port} (tabela cheia)")
        peer.handle_disconnection(socketPeer)

def handle_tcp_frc_message(peer, args: List[str], socketPeer):
    """Processa mensagem FRC (pedido forçado de ligação)"""
    
    if not args:
        print("[FRC] Erro: seqnumber não fornecido")
        socketPeer.close()
        return
    
    remote_seqnumber = int(args[0])
    remote_ip, remote_port = socketPeer.getpeername()
    print(f"[FRC] Pedido FRC de ligação de {remote_ip}:{remote_port} (seq={remote_seqnumber})")
    
    # Criar objeto Neighbor
    neigh = Neighbor(remote_ip, remote_port, remote_seqnumber, socketPeer, "pendente")
    
    # Tentar adicionar como vizinho interno com FRC
    result, removed_neighbor = peer.add_internal_neighbor(neigh, isFrc=True)
    
    if result == neighbor_manager.NeighborAddResult.ACCEPT or result == neighbor_manager.NeighborAddResult.ALREADY_NEIGHBOR:
        # Aceitar ligação
        print(f"[FRC] Ligação aceite com {remote_ip}:{remote_port}")
        peer.queue_tcp_message(socketPeer, "CNF\n")
    elif result == neighbor_manager.NeighborAddResult.ACCEPT_WITH_REPLACEMENT:
        # Aceitar ligação e expulsar vizinho
        print(f"[FRC] Ligação aceite com {remote_ip}:{remote_port}, expulsando vizinho seq={removed_neighbor.seqnumber}")
        peer.queue_tcp_message(socketPeer, "CNF\n")
        
        # Fechar conexão com o vizinho expulso
        if removed_neighbor.socket_fd:
            removed_neighbor.socket_fd.close()
            if removed_neighbor.socket_fd in peer.inputs:
                peer.inputs.remove(removed_neighbor.socket_fd)
            if removed_neighbor.socket_fd in peer.outputs:
                peer.outputs.remove(removed_neighbor.socket_fd)
    else:
        # Rejeitar ligação
        print(f"[FRC] Ligação rejeitada com {remote_ip}:{remote_port}")
        socketPeer.close()
        if socketPeer in peer.inputs:
            peer.inputs.remove(socketPeer)

def handle_tcp_cnf_message(peer, args: List[str], socketPeer):
    """Processa mensagem CNF (confirmação de ligação)"""
    remote_ip, remote_port = socketPeer.getpeername()
    print(f"[CNF] Ligação confirmada com {remote_ip}:{remote_port}")
    
    # Marcar vizinho como ativo
    for neighbor in peer.internal_neighbors + peer.external_neighbors:
        if neighbor.socket_fd == socketPeer:
            neighbor.status = "ativo"

            print(f"[CNF] Vizinho {remote_ip}:{remote_port} marcado como ativo")
            return

def handle_tcp_peer_message(peer, message: str, socketPeer):
    """Processa mensagens TCP recebidas de outros peers (LNK, FRC, QUERY, etc)"""
    print(f"[TCP Peer] {message.strip()}")
    parts = message.strip().split()
    if not parts:
        return
    cmd = parts[0].lower()
    args = parts[1:]
    
    if cmd == "lnk":
        handle_tcp_lnk_message(peer, args, socketPeer)
    elif cmd == "frc":
        handle_tcp_frc_message(peer, args, socketPeer)
    elif cmd == "cnf":
        handle_tcp_cnf_message(peer, args, socketPeer)
    elif cmd == "qry":
        handle_tcp_query_message(peer, args, socketPeer)
    elif cmd == "fnd":
        handle_tcp_fnd_message(peer, args, socketPeer)
    elif cmd == "notfnd":
        handle_tcp_notfnd_message(peer, args, socketPeer)
    else:
        print(f"Comando TCP não reconhecido: {cmd}")
