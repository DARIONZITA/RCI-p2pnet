# Testes para William — Como validar cada tarefa

Este documento explica, em passos simples, como testar cada uma das tarefas atribuídas a William.
Siga os passos em terminais separados conforme indicado e verifique os resultados esperados.

Pré-requisitos:
- Abra 3 terminais (ou mais) no Windows PowerShell.
- No Terminal 1 inicie o servidor: (diretório do projecto)

```powershell
python server.py 58000
```

Observação: execute os peers a partir da pasta `_client` se necessário:

```powershell
cd _client
python client.py -l 58001
```

---

## 1) `handle_leave` — Como testar
Objetivo: verificar que o peer se desregista no servidor e fecha todas as conexões TCP.

Passos:
1. Terminal A: servidor já a correr (porta 58000).
2. Terminal B: inicie Peer1 (ex: `python client.py -l 58001`) e digite `join` para se registar.
3. Terminal C: inicie Peer2 (ex: `python client.py -l 58002`) e digite `join`.
4. Em Peer1 (Terminal B) confirme que tem vizinhos (use `show neighbors` depois que a função estiver implementada).
5. Execute o comando `leave` em Peer1.

O que verificar (saída esperada):
- No Peer1: mensagens indicando que o UNR foi enviado e que sockets foram fechados.
- No servidor (Terminal A): a tabela de peers não deve mais conter o seqnumber de Peer1.
- No Peer2: eventualmente deve detectar desconexão do Peer1 (dependendo do código de deteção).

Verificação detalhada:
- O `peer.send_udp_unr(peer.getSeqnumber())` deve ser chamado — no servidor, uma chamada UNR aparece no log.
- Todos os sockets em `peer.inputs`/`peer.outputs` do Peer1 devem ter sido removidos.
- `peer.internal_neighbors` e `peer.external_neighbors` devem estar vazias.

Dicas de resolução de problemas:
- Se o servidor ainda mostra o peer depois de `leave`, verifique se `send_udp_unr` está a usar o seqnumber correto.
- Se outros peers não percebem a desconexão, verifique se os sockets foram realmente fechados (procure exceções no log).

---

## 2) `handle_release` — Como testar
Objetivo: remover um vizinho específico pelo seu `seqnumber`.

Passos:
1. Inicie servidor e dois peers (Peer1 e Peer2) e faça `join` em ambos.
2. Em Peer1 use `show neighbors` para ver o `seqnumber` do Peer2.
3. Em Peer1 execute: `release <seqnumber_do_Peer2>`.

O que verificar:
- Peer1 deve imprimir mensagem confirmando remoção do vizinho.
- Socket da ligação deve ser fechado e removido de `peer.inputs`/`peer.outputs`.
- Se Peer1 ficar sem vizinhos externos, deve enviar `PEERS` ao servidor (ver log do servidor ou do peer).
- Peer2 deve eventualmente detectar a desconexão (ver logs do Peer2).

Cenários de teste:
- Tentar `release 999` (seq inválido) — o comando deve recusar e informar "não encontrado".

---

## 3) `handle_unpost` — Como testar
Objetivo: remover um identificador localmente.

Passos:
1. Inicie um peer e use `post myfile` (Bernardo implementa POST) para adicionar um identificador.
2. Verifique com `list identifiers` que `myfile` aparece.
3. Execute `unpost myfile`.

O que verificar:
- `list identifiers` deixa de listar `myfile`.
- Mensagem clara informando que o identificador foi removido.
- Tentar `unpost naoexiste` deve produzir mensagem de erro amigável.

---

## 4) `handle_exit` — Como testar
Objetivo: sair da aplicação chamando internamente `handle_leave` e fechando sockets.

Passos:
1. Inicie servidor e peer(s).
2. No peer execute `exit`.

O que verificar:
- O peer deve primeiro executar os passos de `leave` (ver mensagens de UNR e sockets fechados).
- Após breve espera, a aplicação termina (`sys.exit(0)`).
- No servidor, o peer deve ter sido desregistrado.

Dica: se quiser inspecionar, substitua temporariamente `sys.exit(0)` por uma mensagem para confirmar que `handle_leave` foi executado antes de encerrar.

---

## Notas finais e comandos úteis
- Para reiniciar um peer, feche e execute novamente `python client.py -l <porta>`.
- Ver logs do servidor para confirmar `REG`/`UNR`/`PEERS`.
- Se tiver dúvidas, cole aqui a saída dos terminais para eu ajudar a analisar.
