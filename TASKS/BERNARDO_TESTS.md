# Testes para Bernardo — Como validar cada tarefa

Instruções simples para testar cada função atribuída a Bernardo. Use terminais separados para servidor e peers.

Pré-requisitos:
- Terminal 1: servidor

```powershell
python server.py 58000
```

- Terminal 2 e 3: peers (ex: `python client.py -l 58001` e `python client.py -l 58002`), execute `join` em ambos.

---

## 1) `handle_show_neighbors` — Como testar
Objetivo: garantir que o comando lista corretamente vizinhos internos e externos.

Passos:
1. Inicie dois peers e faça `join` em ambos.
2. Em Peer1 execute `show neighbors`.

O que verificar (saída esperada):
- Se não existirem vizinhos: mostrar "Nenhum vizinho conectado".
- Lista de Vizinhos Internos: cada linha `IP:porta#seqnumber [status]`.
- Lista de Vizinhos Externos: mesma formatação.
- Resumo final com contadores e limites (ex: "Internos: 1/4").

Cenários:
- Testar com 0 vizinhos, 1 vizinho e vários vizinhos.

---

## 2) `handle_post` — Como testar
Objetivo: adicionar um identificador local para que seu peer passe a partilhá-lo.

Passos:
1. Em um peer execute `post music1`.
2. Execute `list identifiers` para confirmar que `music1` aparece.
3. Execute `post music1` novamente — deve recusar como duplicado.

O que verificar:
- Mensagem de confirmação quando adicionar.
- Mensagem de aviso quando tentar duplicar.

---

## 3) `handle_list_identifiers` — Como testar
Objetivo: mostrar todos os identificadores locais.

Passos:
1. Adicionar alguns identificadores com `post id1`, `post id2`.
2. Executar `list identifiers`.

O que verificar:
- Impressão numerada dos identificadores (1. id1, 2. id2).
- Mensagem "Nenhum identificador conhecido" se a lista estiver vazia.

---

## Dicas de verificação cruzada
- Use `search <identifier>` em outro peer para validar que os identificadores aparecem na pesquisa (quando o sistema de pesquisa estiver activo).
- Se `post` não adicionar, verifique se `peer.identifiers.addIdentifier` está a ser chamado e persiste na instância do peer.

---

Se quiser, posso implementar automaticamente testes unitários simples ou scripts de integração que abram múltiplos processos e validem saídas — quer que eu crie uma versão básica de teste automatizado?