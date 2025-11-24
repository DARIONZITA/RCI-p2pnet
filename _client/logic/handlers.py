import sys
from common.models import QueryState

def handle_join(peer, args):
    print("Comando JOIN recebido")
    print("Enviando REG ao servidor...")
    peer.send_udp_reg()

def handle_leave(peer, args):
    print("Comando LEAVE recebido")
    # TODO: Implementar LEAVE - William
    # Explicação simples:
    # Este comando faz seu nó "sair" da rede. Primeiro informa o servidor central
    # que você não quer mais estar registado, depois fecha todas as conexões TCP
    # que você tem com outros peers e limpa as listas locais para não manter
    # referências a quem já não está conectado.
    # O que chamar / funções úteis:
    # - `peer.send_udp_unr(peer.getSeqnumber())`  -> envia UNR (unregister) ao servidor UDP
    # - Para cada vizinho em `peer.internal_neighbors + peer.external_neighbors`:
    #     - `if neighbor.socket_fd: neighbor.socket_fd.close()`  -> fecha a conexão TCP
    #     - remover esse socket de `peer.inputs` e `peer.outputs` para o select() parar de monitorar
    # - `peer.internal_neighbors.clear()` e `peer.external_neighbors.clear()` -> limpar as listas locais
    # Feedback ao usuário: imprimir mensagens que confirmem que saiu e que sockets foram fechados

def handle_show_neighbors(peer, args):
    print("Comando SHOW NEIGHBORS recebido")
    
    # Obter os vizinhos internos e externos
    internal_neighbors = peer.internal_neighbors
    external_neighbors = peer.external_neighbors
    
    # Contadores
    total_internal = len(internal_neighbors)
    total_external = len(external_neighbors)
    total_neighbors = total_internal + total_external
    max_neighbors = peer.args.neighMx
    
    print(f"\n=== VIZINHOS DO NÓ {peer.ip}:{peer.port} ===")
    print(f"Total: {total_neighbors}/{max_neighbors} (Limite: {max_neighbors})")
    print(f"Internos: {total_internal} | Externos: {total_external}")
    print("-" * 60)
    
    # Mostrar vizinhos internos
    if internal_neighbors:
        print("\nVizinhos Internos (conexões aceitas por você):")
        print("IP:Porta".ljust(25) + "Nº Sequência".ljust(15) + "Status")
        print("-" * 50)
        
        for i, neighbor in enumerate(internal_neighbors, 1):
            status = getattr(neighbor, 'status', 'ativo')
            print(f"{i:2d}. {neighbor.ip}:{neighbor.port}".ljust(25) + 
                  f"{neighbor.seqnumber}".ljust(15) + 
                  f"{status}")
    else:
        print("\nNenhum vizinho interno.")
    
    # Mostrar vizinhos externos
    if external_neighbors:
        print("\nVizinhos Externos (conexões iniciadas por você):")
        print("IP:Porta".ljust(25) + "Nº Sequência".ljust(15) + "Status")
        print("-" * 50)
        
        for i, neighbor in enumerate(external_neighbors, 1):
            status = getattr(neighbor, 'status', 'ativo')
            print(f"{i:2d}. {neighbor.ip}:{neighbor.port}".ljust(25) + 
                  f"{neighbor.seqnumber}".ljust(15) + 
                  f"{status}")
    else:
        print("\nNenhum vizinho externo.")
    
    # Informação sobre capacidade
    if total_neighbors >= max_neighbors:
        print(f"\n⚠️  ATENÇÃO: Limite máximo de {max_neighbors} vizinhos atingido!")
    elif total_neighbors == 0:
        print(f"\n💡 Dica: Use 'CONNECT <ip> <porta>' para adicionar vizinhos.")
    
    print()
def handle_release(peer, args):
    print("Comando RELEASE recebido")
    # TODO: Implementar RELEASE - William
    # Explicação simples:
    # Remove um vizinho específico identificado pelo seu seqnumber. Serve para
    # forçar a remoção de uma conexão (por exemplo, cancelar uma ligação interna).
    # O que chamar / funções úteis:
    # - Validar que `args` contém um número (seqnumber)
    # - `removed = peer.remove_neighbor_by_seq(seqnumber)` -> retorna o objeto neighbor removido ou None
    # - Se `removed` não for None:
    #     - `if removed.socket_fd: removed.socket_fd.close()` -> fecha a conexão TCP
    #     - remover o socket de `peer.inputs` e `peer.outputs` caso presente
    #     - verificar se ficou sem vizinhos externos: se sim, chamar `peer.send_udp_peers()` para pedir novos peers
    # - Mostrar mensagem de sucesso ou "vizinho não encontrado"

def handle_post(peer, args):
    print("Comando POST recebido")
    
    # Verificar se foi fornecido um identificador
    if not args:
        print("❌ Erro: É necessário especificar um identificador.")
        print("   Uso: POST <identificador>")
        return
    
    # Obter o identificador (pode ser o nome de um ficheiro, por exemplo)
    identifier = args[0]
    
    print(f"📝 Tentativa de adicionar identificador: '{identifier}'")
    
    # Verificar se o identificador já existe
    if peer.identifiers.hasIdentifier(identifier):
        print(f"ℹ️  O identificador '{identifier}' já existe na lista local.")
        return
    
    # Adicionar o identificador à lista local
    try:
        peer.identifiers.addIdentifier(identifier)
        print(f"✅ Identificador '{identifier}' adicionado com sucesso à lista local.")
        
        # Mostrar estatísticas atualizadas (opcional)
        total_identifiers = len(peer.identifiers.getIdentifiers()) if hasattr(peer.identifiers, 'getIdentifiers') else "N/A"
        print(f"📊 Total de identificadores na lista local: {total_identifiers}")
        
    except Exception as e:
        print(f"❌ Erro ao adicionar identificador '{identifier}': {e}")

def handle_unpost(peer, args):
    print("Comando UNPOST recebido")
    # TODO: Implementar UNPOST - William
    # Explicação simples:
    # Remove um identificador da sua lista local (por exemplo quando deixa de
    # partilhar um ficheiro). Não aciona mensagens de rede, apenas limpa o estado.
    # O que chamar / funções úteis:
    # - Verificar `args` e obter `identifier = args[0]`
    # - `peer.identifiers.hasIdentifier(identifier)` -> checar existência
    # - `peer.identifiers.removeIdentifier(identifier)` -> remover se existir
    # - Mostrar mensagem de confirmação ou aviso se o identificador não existe

def handle_list_identifiers(peer, args):
    print("Comando LIST IDENTIFIERS recebido")
    
    # Obter a lista de identificadores
    try:
        identifiers = peer.identifiers.listIdentifiers()
    except AttributeError:
        print("❌ Erro: Não foi possível aceder à lista de identificadores.")
        return
    except Exception as e:
        print(f"❌ Erro inesperado ao obter identificadores: {e}")
        return
    
    # Verificar se a lista está vazia
    if not identifiers:
        print("📭 Nenhum identificador conhecido.")
        print("💡 Use o comando 'POST <identificador>' para adicionar identificadores.")
        return
    
    # Mostrar a lista de identificadores
    print(f"\n📋 IDENTIFICADORES CONHECIDOS ({len(identifiers)} total):")
    print("-" * 50)
    
    for i, identifier in enumerate(identifiers, 1):
        print(f"{i:3d}. {identifier}")
    
    print("-" * 50)
    print(f"📊 Total: {len(identifiers)} identificador(es)")
    
    # Informação adicional sobre o estado
    if hasattr(peer.identifiers, 'hasIdentifier'):
        print("\n💡 Estes identificadores estão disponíveis para outros peers encontrarem.")



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
