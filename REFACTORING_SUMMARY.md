# Resumo da Refatoração de Métodos - client.py

## 📋 Métodos Renomeados

### 🔄 Antes → Depois

1. **`tcp_connect_to_peer(s)`** → **`accept_incoming_connection(server_socket)`**
   - **Responsabilidade**: Aceitar novas conexões TCP de entrada
   - **Quando é chamado**: Quando o socket servidor TCP está pronto para aceitar
   - **O que faz**: 
     - Aceita a conexão
     - Adiciona aos inputs
     - Inicializa fila de mensagens
     - (TODO: Aguardar LNK antes de adicionar como vizinho)

2. **`process_message_server(message)`** → **`handle_udp_response(message)`**
   - **Responsabilidade**: Processar respostas UDP do servidor central
   - **Quando é chamado**: Quando recebe dados no socket UDP
   - **O que faz**: Parsear SQN, LST, OK, NOK do servidor

3. **`process_message_client(message)`** → **`handle_tcp_peer_message(message)`**
   - **Responsabilidade**: Processar mensagens TCP de outros peers
   - **Quando é chamado**: Quando recebe dados de um peer via TCP
   - **O que faz**: Parsear LNK, FRC, QUERY, CONTENT, etc

4. **`tcp_send_command(soc_peer, message)`** → **`queue_tcp_message(peer_socket, message)`**
   - **Responsabilidade**: ADICIONAR mensagem à fila (não envia imediatamente)
   - **Quando é chamado**: Quando queres enviar uma mensagem para um peer
   - **O que faz**: 
     - Adiciona mensagem à fila
     - Adiciona socket aos outputs (para select detectar)

5. **`handle_tcp_message_send(s)`** → **`flush_tcp_queue(peer_socket)`**
   - **Responsabilidade**: ENVIAR a próxima mensagem da fila
   - **Quando é chamado**: Quando select() indica que o socket está pronto para escrever
   - **O que faz**: 
     - Retira mensagem da fila
     - Envia via socket
     - Remove dos outputs se fila vazia

---

## 🎯 Clareza Semântica

### ✅ Agora está claro:

- **`queue_tcp_message()`** = Enfileirar (adicionar à fila)
- **`flush_tcp_queue()`** = Enviar (esvaziar a fila)

### ❌ Antes estava confuso:

- **`tcp_send_command()`** = Parecia que enviava, mas só enfileirava
- **`handle_tcp_message_send()`** = Nome muito genérico

---

## 📊 Fluxo de Envio de Mensagens TCP

```
1. Código chama: queue_tcp_message(peer_socket, "LNK 1234\n")
   ↓
2. Mensagem adicionada à fila: all_messages_to_send[peer_socket] = ["LNK 1234\n"]
   ↓
3. Socket adicionado aos outputs
   ↓
4. select() detecta que socket está pronto para escrever
   ↓
5. Loop chama: flush_tcp_queue(peer_socket)
   ↓
6. Mensagem enviada via socket.send()
   ↓
7. Se fila vazia, socket removido dos outputs
```

---

## 🔍 Métodos UDP (já estavam claros)

- **`send_udp_reg()`** - Envia REG ao servidor
- **`send_udp_unr(seqnumber)`** - Envia UNR ao servidor
- **`send_udp_peers()`** - Envia PEERS ao servidor

---

## 📝 Próximos Passos Sugeridos

1. Implementar parsing em `handle_udp_response()` para SQN/LST/OK/NOK
2. Implementar parsing em `handle_tcp_peer_message()` para LNK/FRC/QUERY/etc
3. Usar `queue_tcp_message()` nos handlers de comandos CLI
4. Implementar lógica de JOIN que:
   - Envia REG via UDP
   - Recebe SQN
   - Envia PEERS via UDP
   - Recebe LST
   - Conecta aos peers via TCP
   - Envia LNK via `queue_tcp_message()`
