import sys
from common.models import QueryState

def handle_join(peer, args):
    print("Comando JOIN recebido")
    print("Enviando REG ao servidor...")
    peer.send_udp_reg()
    peer.send_udp_peers()

def handle_leave(peer, args):
    print("Comando LEAVE recebido")
    print("Enviando UNR ao servidor...")
    peer.send_udp_unr(peer.getSeqnumber())
    
    # Fechar todas as conexões TCP com vizinhos
    all_neighbors = peer.internal_neighbors + peer.external_neighbors
    for neighbor in all_neighbors:
        if neighbor.socket_fd:
            if neighbor.socket_fd in peer.inputs:
                peer.inputs.remove(neighbor.socket_fd)
            if neighbor.socket_fd in peer.outputs:
                peer.outputs.remove(neighbor.socket_fd)
            neighbor.socket_fd.close()
            if getattr(neighbor, 'ip', None):
                print(f"Conexão fechada com {neighbor.ip}:{neighbor.port}")
            else:
                print(f"Conexão fechada com seq={neighbor.seqnumber}")
    
    # Limpar as listas de vizinhos
    peer.internal_neighbors.clear()
    peer.external_neighbors.clear()
    print("Saiu da rede com sucesso")

def handle_show_neighbors(peer, args):
    print("Comando SHOW NEIGHBORS recebido")
    total_internos = len(peer.internal_neighbors)
    total_externos = len(peer.external_neighbors)
    total = total_internos + total_externos
    
    print(f"\nVizinhos: {total}/{peer.args.neighMx}")
    print(f"Internos: {total_internos} | Externos: {total_externos}\n")
    
    if total == 0:
        print("Nenhum vizinho conectado")
        return
    
    if peer.internal_neighbors:
        print("=== Vizinhos Internos ===")
        for neighbor in peer.internal_neighbors:
            print(f"  seq: {neighbor.seqnumber} (status: {neighbor.status})")
    
    if peer.external_neighbors:
        print("\n=== Vizinhos Externos ===")
        for neighbor in peer.external_neighbors:
            print(f"  {neighbor.ip}:{neighbor.port} (seq: {neighbor.seqnumber}, status: {neighbor.status})")

def handle_release(peer, args):
    print("Comando RELEASE recebido")
    if not args:
        print("Erro: Forneça o seqnumber do vizinho a remover")
        return
    
    try:
        seqnumber = int(args[0])
    except ValueError:
        print("Erro: Seqnumber deve ser um número")
        return
    
    removed = peer.remove_neighbor_by_seq(seqnumber)
    
    if removed is None:
        print(f"Vizinho com seqnumber {seqnumber} não encontrado")
        return
    
    # Fechar o socket se existir
    if removed.socket_fd:
        if removed.socket_fd in peer.inputs:
            peer.inputs.remove(removed.socket_fd)
        if removed.socket_fd in peer.outputs:
            peer.outputs.remove(removed.socket_fd)
        removed.socket_fd.close()
    
    print(f"Vizinho seq={seqnumber} removido com sucesso")
    
    # Se ficou sem vizinhos externos, pedir novos peers
    if not peer.external_neighbors:
        print("Sem vizinhos externos! Solicitando lista de peers...")
        peer.send_udp_peers()

def handle_post(peer, args):
    print("Comando POST recebido")
    if not args:
        print("Erro: Forneça o identificador a adicionar")
        return
    
    identifier = args[0]
    
    if peer.identifiers.hasIdentifier(identifier):
        print(f"Identificador '{identifier}' já existe")
        return
    
    peer.identifiers.addIdentifier(identifier)
    print(f"Identificador '{identifier}' adicionado com sucesso")

def handle_unpost(peer, args):
    print("Comando UNPOST recebido")
    if not args:
        print("Erro: Forneça o identificador a remover")
        return
    
    identifier = args[0]
    
    if not peer.identifiers.hasIdentifier(identifier):
        print(f"Identificador '{identifier}' não encontrado")
        return
    
    peer.identifiers.removeIdentifier(identifier)
    print(f"Identificador '{identifier}' removido com sucesso")

def handle_list_identifiers(peer, args):
    print("Comando LIST IDENTIFIERS recebido")
    identifiers = peer.identifiers.listIdentifiers()
    
    if not identifiers:
        print("Nenhum identificador conhecido")
        return
    
    print(f"\nIdentificadores ({len(identifiers)}):")
    for i, identifier in enumerate(identifiers, 1):
        print(f"  {i}. {identifier}")



def handle_search(peer, args):
    print("Comando SEARCH recebido")
    identifier = args[0]
    print("Procurando pelo identificador", identifier)
    print("Procurando no proprio nó\n")
    
    if peer.identifiers.hasIdentifier(identifier):
        print("Identificador encontrado no proprio nó\n")
        return
    
    if peer.args.hopcount > 0:
        print("Identificador nao encontrado no proprio nó\n")
        print("Procurando nos vizinhos\n")
        
        if not peer.internal_neighbors and not peer.external_neighbors:
            print("Nenhum vizinho para consultar\n")
            return

        # Criar estado da query local (requester_socket=None)
        peer.active_queries[identifier] = QueryState(None, identifier, len(peer.internal_neighbors))
        
        query = "QRY " + identifier + " " + str(peer.args.hopcount - 1) + "\n"
        for neighbor in peer.internal_neighbors + peer.external_neighbors:
            peer.queue_tcp_message(neighbor.socket_fd, query)
    else:
        print("Identificador nao encontrado no proprio nó (TTL expirou)\n")
