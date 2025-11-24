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
    # TODO: Implementar SHOW NEIGHBORS - Bernardo
    # Explicação simples:
    # Mostrar para o utilizador quem está ligado ao seu nó. Existem dois tipos de
    # vizinhos: internos (conexões aceitas por você) e externos (conexões iniciadas
    # por você). Para cada vizinho mostramos o IP:porta e o número de sequência.
    # O que chamar / funções úteis:
    # - Ler `peer.internal_neighbors` e `peer.external_neighbors` (listas de objetos)
    # - Para cada neighbor: mostrar `neighbor.ip`, `neighbor.port`, `neighbor.seqnumber`
    # - Opcional: `neighbor.status` se existir (ex: 'ativo' ou 'pendente')
    # - Mostrar contadores: total, internos e externos e o limite `peer.args.neighMx`

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
    # TODO: Implementar POST - Bernardo
    # Explicação simples:
    # Adiciona um identificador (por exemplo o nome de um ficheiro) à sua lista
    # local para que outros peers possam encontrá-lo. Não envia nada pela rede;
    # apenas atualiza o estado local.
    # O que chamar / funções úteis:
    # - Verificar `args` e obter `identifier = args[0]`
    # - `peer.identifiers.hasIdentifier(identifier)` -> retorna True se já tiver
    # - `peer.identifiers.addIdentifier(identifier)` -> adiciona o identificador
    # - Mostrar mensagem confirmando a adição ou informando que já existia

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
    # TODO: Implementar LIST IDENTIFIERS - Bernardo
    # Explicação simples:
    # Mostra todos os identificadores que este nó conhece (os que você adicionou
    # localmente com POST). Serve para confirmar o que está a ser partilhado.
    # O que chamar / funções úteis:
    # - `identifiers = peer.identifiers.listIdentifiers()` -> obtém uma lista de strings
    # - Se a lista estiver vazia: mostrar "Nenhum identificador conhecido"
    # - Caso contrário, iterar com `enumerate(identifiers, 1)` e imprimir cada um
    # - Mostrar o total (len(identifiers))



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
