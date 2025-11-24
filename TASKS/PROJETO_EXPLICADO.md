# 🌐 P2P Overlay Network - Guia Completo

## 📚 O que é este Projeto?

Este é um **sistema de rede P2P (Peer-to-Peer) distribuído** onde múltiplos computadores (peers) se conectam entre si para **compartilhar e pesquisar conteúdos** (identificadores).

### Analogia Simples:
Pense numa **biblioteca distribuída** onde:
- Cada pessoa (peer) tem seus próprios livros (identificadores)
- As pessoas se conectam umas com as outras formando uma rede
- Quando alguém procura um livro, a pergunta passa de pessoa em pessoa até encontrar
- Se alguém sair, a rede se reorganiza para manter-se conectada

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  SERVIDOR UDP (Gerenciador Central)                    │
│  └─ Mantém lista de todos os peers da rede            │
│  └─ Atribui números sequenciais para ordem            │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  PEER A          PEER B          PEER C                │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐         │
│  │ TCP:    │─────│ TCP:    │─────│ TCP:    │         │
│  │ 58001   │     │ 58002   │     │ 58003   │         │
│  └─────────┘     └─────────┘     └─────────┘         │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐         │
│  │ ID:     │     │ ID:     │     │ ID:     │         │
│  │ arq1    │     │ arq2    │     │ arq1    │         │
│  │ arq3    │     │ arq4    │     │ arq2    │         │
│  └─────────┘     └─────────┘     └─────────┘         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔑 Conceitos Importantes

### 1. **Vizinhos Internos vs Externos**

- **Vizinho Interno**: Peer que conectou a você (iniciou a conexão)
  - Exemplo: Peer B conecta a você → B é seu vizinho interno
  
- **Vizinho Externo**: Peer com quem você conectou (você iniciou)
  - Exemplo: Você conecta a Peer C → C é seu vizinho externo

### 2. **Número de Sequência (seqnumber)**

- Atribuído pelo servidor quando você entra
- Ordem de chegada: Primeiro a entrar = 1, segundo = 2, etc
- **Regra importante**: Só pode conectar a peers com números menores
  - Peer 5 pode conectar a peers 1, 2, 3, 4
  - Peer 5 NÃO pode conectar a peer 7

### 3. **N+ e N- (Limite de Vizinhos)**

- **N+**: Máximo de vizinhos externos (que você inicia conexão)
- **N-**: Máximo de vizinhos internos (que conectam a você)
- Ambos têm o mesmo valor (definido no comando de execução)
- Padrão: 2 vizinhos de cada tipo

---

## 📂 Estrutura do Código

### Arquivos Principais

```
_client/
├── client.py              # Ponto de entrada principal
├── core/
│   └── peer.py           # Classe principal do Peer (coordena tudo)
├── logic/
│   ├── handlers.py       # Processa comandos do usuário
│   ├── network.py        # Processa mensagens TCP/UDP
│   ├── transport.py      # Envia mensagens (sockets)
│   └── neighbor_manager.py # Gerencia vizinhos
├── cli/
│   └── interface.py      # Interface de linha de comando
└── common/
    ├── args.py           # Parâmetros de execução
    └── models.py         # Classes Neighbor, QueryState, Identifier
```

### Fluxo de Dados

```
Usuário digita "join"
       ↓
interface.py (cli) → parse comando
       ↓
handlers.py → handle_join()
       ↓
peer.send_udp_reg() → transport.py
       ↓
server.py (UDP) → responde com SQN
       ↓
network.py → handle_udp_response()
       ↓
peer conecta a outros peers via TCP
```

---

## 🚀 Como Executar

### Pré-requisitos
- Python 3.7+
- Terminal/PowerShell
- Estar no diretório `_client/`

### Passo 1: Iniciar o Servidor UDP

```bash
# Na primeira janela de terminal, vá para a pasta p2p
cd c:\Users\DELL\OneDrive\Documents\p2p

# Execute o servidor na porta 58000
python server.py 58000

# Saída esperada:
# Server UDP started on port 58000
```

### Passo 2: Iniciar Peers (Clientes)

**Em janelas separadas**, execute:

```bash
# PEER 1 - Primeira pessoa a entrar
cd c:\Users\DELL\OneDrive\Documents\p2p\_client
python client.py -l 58001 -n 2 -h 3

# PEER 2 - Segunda pessoa
python client.py -l 58002 -n 2 -h 3

# PEER 3 - Terceira pessoa
python client.py -l 58003 -n 2 -h 3
```

**Explicação dos parâmetros:**
- `-l 58001`: Porta TCP onde este peer escuta (deve ser diferente em cada)
- `-n 2`: Máximo 2 vizinhos internos E 2 externos (N+ = N- = 2)
- `-h 3`: Máximo 3 saltos para buscas na rede
- `-s 192.168.56.21`: IP do servidor (padrão, pode omitir)
- `-p 58000`: Porta do servidor (padrão, pode omitir)

### Passo 3: Testar Comandos

Após os peers iniciarem, você verá o prompt `>`

```bash
> join                    # Entrar na rede
> show neighbors          # Ver quem está conectado
> post arquivo1           # Adicionar identificador
> list identifiers        # Ver seus identificadores
> search arquivo2         # Buscar um identificador na rede
> leave                   # Sair da rede
> exit                    # Encerrar aplicação
```

---

## 🧪 Cenários de Teste Recomendados

### **Teste 1: Ciclo Básico (5 minutos)**

```bash
# JANELA 1 (SERVIDOR)
python server.py 58000

# JANELA 2 (PEER 1)
python client.py -l 58001 -n 2 -h 3
> join
> post file1
> post file2
> list identifiers
> show neighbors

# JANELA 3 (PEER 2)
python client.py -l 58002 -n 2 -h 3
> join
> show neighbors      # Deve ver PEER 1
> search file1        # Deve encontrar em PEER 1
> search file2
```

**Esperado:**
- PEER 2 conecta automaticamente a PEER 1
- PEER 2 encontra file1 e file2 que estão em PEER 1
- Ambos os peers mostram um vizinho cada

---

### **Teste 2: Rede Distribuída (10 minutos)**

```bash
# JANELA 1 (SERVIDOR)
python server.py 58000

# JANELA 2 (PEER 1)
python client.py -l 58001 -n 2 -h 3
> join
> post secret1

# JANELA 3 (PEER 2)
python client.py -l 58002 -n 2 -h 3
> join
> show neighbors      # Deve ver PEER 1
> post secret2
> search secret1      # Encontra em PEER 1

# JANELA 4 (PEER 3)
python client.py -l 58003 -n 2 -h 3
> join
> show neighbors      # Deve ver PEER 2
> search secret1      # Encontra passando por PEER 2 → PEER 1
> search secret2      # Encontra em PEER 2
```

**Esperado:**
- PEER 3 conecta a PEER 2
- PEER 3 consegue encontrar secret1 mesmo não conectado diretamente a PEER 1
- A busca passa por múltiplos peers (flooding)

---

### **Teste 3: Recuperação de Rede (10 minutos)**

```bash
# JANELA 1 (SERVIDOR)
python server.py 58000

# JANELA 2 (PEER 1)
python client.py -l 58001 -n 2 -h 3
> join
> post data1

# JANELA 3 (PEER 2)
python client.py -l 58002 -n 2 -h 3
> join
> show neighbors      # Conectado a PEER 1

# JANELA 4 (PEER 3)
python client.py -l 58003 -n 2 -h 3
> join
> show neighbors      # Conectado a PEER 2

# Agora SAIA com PEER 1:
# Em JANELA 2: > leave

# Em JANELA 4, espere alguns segundos e:
> show neighbors      # PEER 2 ainda visível?
# O sistema deve detectar desconexão e tentar reconectar
```

**Esperado:**
- Quando PEER 1 sai, PEER 2 detecta (vizinho externo perdido)
- PEER 2 tenta reconectar ao servidor para novo vizinho
- PEER 3 também sente o impacto da mudança

---

### **Teste 4: Limite de Vizinhos (5 minutos)**

```bash
# Iniciar com N=1 para ver limite
# JANELA 1 (SERVIDOR)
python server.py 58000

# JANELA 2 (PEER 1 - N=1)
python client.py -l 58001 -n 1 -h 3
> join

# JANELA 3 (PEER 2)
python client.py -l 58002 -n 1 -h 3
> join
> show neighbors      # Conectado a PEER 1

# JANELA 4 (PEER 3)
python client.py -l 58003 -n 1 -h 3
> join
> show neighbors      # NÃO consegue conectar (PEER 1 está cheio)
```

**Esperado:**
- PEER 3 tenta conectar mas PEER 1 rejeita (limite atingido)
- Sistema tenta usar FRC (Force) para substituir se necessário

---

## 📊 Monitorar o que Está Acontecendo

### Mensagens Importantes

```
[UDP] Seqnumber atribuído: 1          # Você entrou na rede com seq=1
[TCP] Ligação aceita de X.X.X.X      # Novo vizinho conectou a você
[Connect] Enviando LNK para X.X.X.X  # Você tentou conectar a alguém
[TCP Query] file1 2                   # Recebeu busca por file1 com TTL=2
[Query] Query file1 expirada (timeout) # Busca expirou sem resposta
```

### Verificar Conexões

```bash
# Em cada peer, execute periodicamente:
> show neighbors      # Ver vizinhos atuais
> list identifiers    # Ver o que você tem
```

---

## ⚠️ Problemas Comuns e Soluções

| Problema | Causa | Solução |
|----------|-------|---------|
| "Conexão recusada" ao executar peer | Servidor UDP não está rodando | Inicie `python server.py 58000` primeiro |
| Peers não conectam entre si | Portas TCP iguais em múltiplos peers | Use portas diferentes (-l 58001, -l 58002, etc) |
| "Nenhum peer elegível" | Sem peers com seqnumber menor | Inicie múltiplos peers (primeiro não conecta a ninguém) |
| Busca não encontra identificador | TTL (hopcount) muito baixo | Aumente com `-h 5` ou mais |
| "Limite de vizinhos atingido" | Muitos peers tentando conectar | Aumente N com `-n 3` ou mais |

---

## 🔄 Fluxo de Funcionamento Simplificado

### 1️⃣ Quando você executa `join`

```
1. Enviar REG ao servidor com sua porta TCP
2. Servidor responde com seu seqnumber
3. Pedir lista de todos os peers ao servidor
4. Conectar a peers com seqnumber menor (máximo N+)
5. Esperar por conexões de peers com seqnumber maior
```

### 2️⃣ Quando você executa `post identifier`

```
1. Adicionar identifier à sua lista local
2. Pronto! Outros podem procurar
```

### 3️⃣ Quando você executa `search identifier`

```
1. Verificar se você tem localmente
2. Se não:
   - Enviar QRY para todos os vizinhos com TTL-1
   - Esperar respostas (FND ou NOTFND)
   - Se receber FND: adicionar à sua lista e informar ao usuário
   - Se ninguém responder: informar não encontrado
```

### 4️⃣ Quando você executa `leave`

```
1. Enviar UNR ao servidor para desregistrar
2. Fechar todas as conexões TCP
3. Sair da rede
```

---

## 💾 Divisão de Tarefas

### 🔵 **WILLIAM** - Funcionalidades de Gerenciamento

- **`handle_leave`**: Desregistrar e sair
- **`handle_release`**: Remover um vizinho específico
- **`handle_unpost`**: Remover um identificador
- **`handle_exit`**: Sair completo da aplicação

### 🟢 **BERNARDO** - Funcionalidades de Visualização

- **`handle_show_neighbors`**: Ver vizinhos conectados
- **`handle_post`**: Adicionar identificador
- **`handle_list_identifiers`**: Listar identificadores
- Melhorias na **`handle_search`**: Melhor feedback

---

## 🎯 Objetivos de Implementação

| Status | Tarefa | Responsável |
|--------|--------|-------------|
| ✅ | Servidor UDP funcionando | Já completo |
| ✅ | Peers conectam via TCP | Já completo |
| ✅ | Busca básica (QRY/FND/NOTFND) | Já completo |
| ✅ | Recuperação de rede | Já completo |
| ⏳ | Comandos de interface (7 total) | William (4) + Bernardo (3) |

---

## 📖 Exemplos Práticos

### Exemplo 1: Dois Peers Simples

```bash
# Terminal 1
python server.py 58000

# Terminal 2
python client.py -l 58001
> join
> post music1
> show neighbors
> list identifiers

# Terminal 3
python client.py -l 58002
> join
> show neighbors        # Vê peer em 58001
> search music1         # Encontra
> search music2         # Não encontra
```

### Exemplo 2: Rede com 4 Peers

```bash
Topologia final:
Peer1 (seq=1)
  ↑
Peer2 (seq=2) → conecta a Peer1
  ↑
Peer3 (seq=3) → conecta a Peer2
  ↑
Peer4 (seq=4) → conecta a Peer3

Busca de Peer4 para music1 (em Peer1):
Peer4 → QRY → Peer3 → QRY → Peer2 → QRY → Peer1
Peer1 → FND → Peer2 → FND → Peer3 → FND → Peer4
```

---

## ✨ Resumo

| Aspecto | Descrição |
|---------|-----------|
| **O quê** | Rede P2P distribuída para compartilhar identificadores |
| **Como** | Cada peer conecta a outros via TCP, busca via flooding |
| **Por que** | Aprender redes, protocolos e sistemas distribuídos |
| **Resultado** | Sistema resiliente que se auto-reorganiza |

---

**Bom desenvolvimento! 🚀**

Para dúvidas durante a implementação, consulte os comentários TODO nos respectivos arquivos.
