# Relatório do Projecto p2pnet

Peer-to-Peer Overlay Network
Redes de Computadores I - 2025/26

Grupo: ______
Nome: __________________________ Número: ______ E-mail: ____________________
Nome: __________________________ Número: ______ E-mail: ____________________
Nome: __________________________ Número: ______ E-mail: ____________________

---

## 1. Introdução

Este projeto implementa um sistema Peer-to-Peer (P2P) com um diretório central simples (servidor UDP) que organiza e permite aos peers descobrirem-se e conectarem-se em ligações TCP ponto-a-ponto. O objetivo é construir uma rede sobreposta para pesquisa de identificadores distribuídos (lookup) suportando: estabelecimento/terminação de ligações, troca de identificadores (post/unpost), consultas (search), e políticas de substituição de vizinhos (FRC).

O objeto de estudo foi a construção de um overlay simples que demonstra mecanismos de descoberta (servidor) e manutenção de vizinhança (neighbors internos/externos), assim como a propagação controlada de queries com TTL (hopcount).

## 2. Realizações

A tabela a seguir indica o estado de implementação de cada funcionalidade requerida.

| Funcionalidade | Implementada (Completamente / Parcialmente / Não) | Observações |
|---|---|---|
| Servidor de peers | Implementada Completamente | `server.py` - servidor UDP que suporta REG/UNR/PEERS e persiste `peerTable.txt`. |
| Interface do utilizador | Implementada Completamente | CLI em `_client/cli/interface.py`, comandos: `join`, `leave`, `show neighbors`, `post`, `unpost`, `list identifiers`, `search`, `exit`. |
| Cliente para consulta do servidor de peers | Implementada Completamente | `_client/core/peer.py` + `logic/transport.py` implementam REG/UNR/PEERS via UDP. |
| Protocolo para estabelecimento e terminação de ligações na rede sobreposta | Implementada Completamente | Mensagens TCP: `LNK`, `FRC`, `CNF` para estabelecimento; `UNR` + encerramento de sockets para terminar ligações. Politica de substituição via FRC e regras por seqnumber implementadas. |
| Protocolo para pesquisa de identificadores na rede | Implementada Completamente | `QRY`/`FND`/`NOTFND` com hopcount (TTL) e propagação controlada; handlers em `logic/network.py`/`logic/handlers.py`. |
| Optimizações | Parcialmente Implementada | Backoff de candidatos falhados e lógica de recovery externo (FRC usado apenas em recuperação); não há compressão, caching além de inserir identifier local quando um `FND` retorna. |

### 2.1 Optimizações implementadas
- Backoff temporário para candidatos que falharam em estabelecer ligação (evita tentativas repetidas por `failed_candidate_ttl`).
- Utilização de FRC como mecanismo de recovery para reestruturar vizinhança quando não se tem vizinhos externos.
- TTL (hopcount) para limitar propagação de queries e reduzir tráfego.
- `select()` loop non-blocking e filas de envio TCP para evitar bloqueios.

## 3. Arquitectura

Arquitectura geral: um pequeno servidor UDP centralizado para descoberta e bootstrap (registro e lista de peers), e peers que se ligam via TCP para formar a rede sobreposta (overlay). A comunicação cliente-servidor é feita por mensagens UDP simples (REG/UNR/PEERS). A comunicação entre peers usa TCP com mensagens de controle e de aplicação.

Exemplo de arquitetura (ASCII, cliente <-> servidor e peers):

```
            +---------------+
            | Peer A        |<--TCP--> Peer B
            | (lnkport:8081)|          (lnkport:8082)
            +---------------+\
               | UDP REG/PEERS \               +-------------+
               v               \              | Peer C      |
            +---------------+   \------------->| (lnk:8083)  |
            | Discovery     | UDP  (REG/PEERS) +-------------+
            | Server (UDP)  | <- - - - - - - - - - - - - - - -
            +---------------+
```

### 3.1 Estruturas de dados mantidas pelo servidor e pelo cliente

Server (`server.py`):
- peerTable: lista de dicionários com chaves `ip`, `lnkport`, `seqnumber`. Persiste em `peerTable.txt` na saída do servidor (um par por linha com `ip:port#seq`).

Client/Peer (`_client/core/peer.py` e `common/models.py`):
- `internal_neighbors`: lista de objetos `Neighbor` (sem IP/port para interna; usa socket e seqnumber).
- `external_neighbors`: lista de `Neighbor` (ip, port, seqnum, socket_fd, status).
- `identifiers`: instância `Identifier` (lista simples de strings).
- `active_queries`: mapa identifier -> `QueryState` com `requester_socket`, `pending_count`.
- `eligible_peers`: lista de candidaturas recebidas da lista `PEERS` do servidor.
- `all_messages_to_send`: dicionário socket -> lista de mensagens pendentes.
- `query_timeouts`: mapa identifier -> timestamp (para limpeza de queries expiradas).

Observação: a maioria das estruturas é implementada usando estruturas nativas Python (listas, dicionários). Tipos/enum são definidos em `common/models.py`.

### 3.2 Descrição dos protocolos cliente-servidor e peer-to-peer

Abaixo, descrevemos o protocolo da camada de aplicação (formato de mensagens) e um resumo do comportamento com diagramas espaço-tempo simplificados.

1) Estabelecimento e Terminação de ligações na rede sobreposta
- Mensagens UDP para servidor (registro/bootstrap):
  - `REG <lnkport>`: peer pede registro; servidor responde `SQN <seqnumber>` (assigna seqnumber crescente). Implementado em `server.py` e `_client/logic/transport.py`.
  - `UNR <seqnumber>`: peer pede desregistro; servidor responde `OK` ou `NOK`.
  - `PEERS`: server responde `LST\n ip:port#seqnumber\n ...`.

- Mensagens TCP entre peers (estabelecimento):
  - `LNK <seqnumber>`: pedido normal de ligação (peer de seq menor liga para maior); o receptor aceita ou rejeita.
  - `FRC <seqnumber>`: pedido com força (force connection) para expulsar um vizinho com seq mais alto se a tabela estiver cheia.
  - `CNF`: confirmação da ligação, enviada quando o receptor aceitou.
  - Quando se termina ligação localmente: o peer pode fechar sockets; se remover por `UNR`, desconecta com todos os vizinhos também.

Diagrama espaço-tempo (Estabelecimento):
```
Peer A                       Peer B
   |  connect (LNK 5)             |
   | -------------------------->  |
   |                             | check seq, accept/reject
   |                             | reply CNF or close
   | <--------------------------  |
   | CNF                          |
```

2) Protocolos de pesquisa de identificadores
- Mensagens TCP de SEARCH (propagação com hopcount):
  - `QRY <identifier> <hopcount>`: pedido de pesquisa, decrementando hopcount a cada hop.
  - `FND <identifier>`: resposta quando encontrado.
  - `NOTFND <identifier>`: resposta quando não encontrado em vizinhos e TTL expira.

- O peer que origina uma query cria `QueryState` para rastrear respostas pendentes (contagem `pending_count`); quando todas respondem `NOTFND` envia `NOTFND` localmente, quando qualquer `FND` chega propaga `FND` de volta e registra localmente o identificador (cache local).

Diagrama espaço-tempo (Query):
```
Peer A                     Peer B                      Peer C
  | QRY X 2  |                 |                    
  |---------->| QRY X 1        |                    
  |           |--------------->| QRY X 0            
  |           |<-------------- | NOTFND X           
  |<----------| NOTFND X       |
```

3) Outras operações com identificadores
- `POST <id>` (local): adiciona ao conjunto de `identifiers` do peer.
- `UNPOST <id>`: remove localmente.
- `LIST IDENTIFIERS`: lista os identificadores locais.

3.3 Outros recursos de desenho relevantes
- Política de substituição pelo seqnumber: peers com seqnumbers mais altos são preferencialmente expulsos por FRC quando ocorre recovery; isso favorece manter nós com seqnumbers mais baixos (potencialmente mais antigos) na topologia.
- Backoff para candidatos falhados (evitar tentativas repetidas imediatas): quando uma conexão falha, o par (ip,port,seq) é marcado até `failed_candidate_ttl` segundos.
- Mecanismo de recovery: quando um peer fica sem vizinhos externos, solicita `PEERS` ao servidor e tenta reconexão; a primeira tentativa de recovery pode usar `FRC`.

## 4. Implementação

### Linguagem e plataforma
- Python 3. Implementação portátil (localhost ou VM), testado com sockets IPv4.
- Arquitetura: um servidor UDP central (`server.py`) e peers implementados em `_client/`.

### Bibliotecas externas
- Nenhuma dependência externa além da biblioteca padrão do Python (`socket`, `select`, `sys`, `signal`, etc.).

### Threads e loop de eventos
- Não há threads; peers usam `select()` (I/O multiplexing) para gerir sockets e `sys.stdin` para CLI (loop principal em `_client/core/peer.py`).

### Sockets e comunicações
- Servidor: UDP (`socket.SOCK_DGRAM`), aguardando REG/UNR/PEERS; responde conforme protocolo; guarda a `peerTable` em `peerTable.txt` quando encerrado por sinal (SIGINT/SIGTERM).
- Peer: utiliza um socket UDP para comunicação com o servidor e sockets TCP (server/listening) para receber ligações; sockets TCP são non-blocking com filas de mensagens por socket (`all_messages_to_send`), e `select()` gere leitura/escrita/except.

### Estado persistente no servidor
- `peerTable` é persistido para `peerTable.txt` no servidor. Peers guardam pouco estado local (identifiers) em memória apenas; não há persistência de identifiers por ficheiro.

### Ambiente de execução
- Pode ser executado em `localhost` (testes) ou em VMs (por exemplo, Vagrantfile disponível em `_client/` para testes mais controlados).

## 5. Limitações

- Sem autenticação / segurança: mensagens e peers não autentificados (ninguém verifica identidade) → vulnerável a spoofing.
- UDP sem retransmissão: mensagens UDP (REG/PEERS/UNR) não são retransmitidas, logo possíveis perdas resultam em falta de atualização do `peerTable`.
- Falta de NAT traversal: não há STUN/TURN; peers atrás de NAT podem ter problemas para aceitar ligações de entrada.
- Gestão de falhas simples: detecção por socket closed; não há reconciliação detalhada em caso de partições prolongadas.
- Não há replicação do `peerTable` no servidor e não há redundância do servidor (single point of failure).
- Identificadores mantidos apenas em memória (não persistidos localmente) e sincronização eventual via queries.

## 6. Conclusões

O projeto implementa uma rede sobreposta funcional com discovery centralizado e protocolos P2P para ligação e pesquisa. As regras de FRC e política por seqnumber proporcionam um mecanismo simples de reordenamento e manutenção da topologia. O sistema é adequado para fins pedagógicos: demonstra conceitos de bootstrap, vizinhança, propagação de queries com TTL e políticas de substituição.

Para produção seria necessário acrescentar: segurança/autenticação, maior robustez contra perdas de UDP, NAT traversal, replicação do servidor ou um servidor distribuído, e persistência local de estado de peer/identifiers.

## 7. Link do Repositório

- URL do repositório: <colocar o link do GitHub aqui>

## Execução e testes rápidos ✅

Para testar localmente (ex.: 2-3 instâncias de peer e 1 servidor):

1) Executar o servidor (UDP):

```powershell
python server.py 58000
```

2) Executar um peer (em terminais separados ou VMs):

```powershell
python _client/client.py -s 127.0.0.1 -p 58000 -l 8081
python _client/client.py -s 127.0.0.1 -p 58000 -l 8082
```

3) No prompt do peer, usar comandos:
- `join` → regista no servidor e solicita lista de peers
- `post <id>` → adiciona identificador local
- `search <id>` → procura na rede com TTL definido em `-h`
- `show neighbors` → mostra vizinhos internos/externos
- `leave` → desregistra e desconecta

Observação: para testes em hosts diferentes, substituir `127.0.0.1` pelo IP do servidor e ajustar portas conforme necessário.

## 8. Referências bibliográficas

- Kurose, James, and Keith Ross. Computer Networking: A Top-Down Approach.
- Documentação Python `socket` e `select`.
- Notas de aula de Redes de Computadores I (município do curso).

---

Arquivo(s de interesse no projeto:
- `server.py`
- `_client/core/peer.py`
- `_client/logic/transport.py`
- `_client/logic/network.py`
- `_client/logic/neighbor_manager.py`
- `_client/common/models.py`
- `_client/cli/interface.py`


*Este relatório foi gerado automaticamente a partir do código presente na workspace.*
