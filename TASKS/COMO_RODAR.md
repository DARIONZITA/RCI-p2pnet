# 🚀 Como Rodar o Projeto P2P

Este guia explica como executar o servidor no Windows (host) e os clientes (peers) dentro da máquina virtual Vagrant.

---

## 📋 Pré-requisitos

Certifique-se de ter instalado:
- **Python 3.7+** no Windows
- **VirtualBox** (para rodar a VM)
- **Vagrant** (para gerenciar a VM)

---

## 🖥️ Passo 1: Iniciar o Servidor (no Windows/Host)

O servidor UDP deve rodar **no seu Windows**, não na VM.

### 1.1 Abra o PowerShell na pasta do projeto

```powershell
cd C:\Users\DELL\OneDrive\Documents\p2p
```

### 1.2 Execute o servidor na porta 58000

```powershell
python server.py 58000
```

**O que você verá:**
```
Servidor UDP rodando na porta 58000
Aguardando comandos...
```

✅ **Deixe este terminal aberto!** O servidor ficará escutando conexões dos peers.

---

## 🐧 Passo 2: Iniciar os Clientes (na VM Vagrant)

Os clientes (peers) rodam **dentro da VM** e comunicam com o servidor no host via rede.

### 2.1 Abra um novo PowerShell na pasta `_client`

```powershell
cd C:\Users\DELL\OneDrive\Documents\p2p\_client
```

### 2.2 Inicie a máquina virtual Vagrant

```powershell
vagrant up
```

**Aguarde:** A primeira vez pode demorar (download da imagem Ubuntu, instalação do Python).

### 2.3 Entre na VM via SSH

```powershell
vagrant ssh
```

Agora você está **dentro da VM** (prompt muda para `vagrant@ubuntu-focal:~$`).

### 2.4 Navegue até a pasta do projeto

```bash
cd p2pnet
```

### 2.5 Execute o primeiro cliente (Peer 1)

```bash
python3 client.py -s 192.168.56.1 -p 58000 -l 58001
```

**Explicação dos parâmetros:**
- `-s 192.168.56.1` → IP do host Windows (onde o servidor está rodando)
- `-p 58000` → Porta do servidor UDP
- `-l 58001` → Porta local do peer (TCP)

**O que você verá:**
```
Peer iniciado na porta 58001
Digite comandos (join, search, post, etc.)
>
```

### 2.6 Registre o peer na rede

```bash
> join
```

Você verá:
```
Comando JOIN recebido
Enviando REG ao servidor...
```

No terminal do **servidor** (Windows) aparecerá:
```
REG recebido de 192.168.56.10:58001
```

---

## 🔄 Passo 3: Adicionar Mais Peers (opcional)

Para testar com múltiplos peers, abra **novos terminais PowerShell** e repita:

### Terminal 2 (Peer 2):
```powershell
cd C:\Users\DELL\OneDrive\Documents\p2p\_client
vagrant ssh
cd p2pnet
python3 client.py -s 192.168.56.1 -p 58000 -l 58002
> join
```

### Terminal 3 (Peer 3):
```powershell
cd C:\Users\DELL\OneDrive\Documents\p2p\_client
vagrant ssh
cd p2pnet
python3 client.py -s 192.168.56.1 -p 58000 -l 58003
> join
```

---

## 🧪 Passo 4: Testar Comandos

Depois de fazer `join`, experimente:

```bash
> post music1              # Adicionar identificador local
> list identifiers         # Ver seus identificadores
> show neighbors           # Ver peers conectados
> search music1            # Procurar identificador na rede
> release 2                # Remover vizinho com seqnumber 2
> leave                    # Sair da rede
> exit                     # Fechar o cliente
```

---

## 🛑 Passo 5: Encerrar Tudo

### 5.1 Parar os clientes
Em cada terminal da VM, digite:
```bash
> exit
```

Depois saia do SSH:
```bash
exit
```

### 5.2 Parar o servidor (Windows)
No terminal do servidor, pressione `Ctrl+C`.

### 5.3 Desligar a VM (opcional)
```powershell
vagrant halt
```

Ou, para destruir completamente a VM:
```powershell
vagrant destroy -f
```

---

## 🔧 Troubleshooting

### ❌ Erro: "Connection refused" ao fazer `join`
- Verifique se o servidor está rodando no Windows.
- Confirme que usou o IP correto (`-s 192.168.56.1`).
- Verifique firewall do Windows (pode bloquear UDP 58000).

### ❌ Erro: "vagrant command not found"
- Instale o Vagrant: https://www.vagrantup.com/downloads

### ❌ Erro: "VBoxManage not found"
- Instale o VirtualBox: https://www.virtualbox.org/wiki/Downloads

### ❌ Peers não se conectam entre si
- Verifique se ambos fizeram `join`.
- Use `show neighbors` para ver conexões.
- Aguarde alguns segundos (conexões TCP levam tempo).

---

## 📝 Resumo Rápido

| Componente | Onde Roda | Comando |
|------------|-----------|---------|
| Servidor UDP | Windows (host) | `python server.py 58000` |
| Cliente (Peer) | VM Vagrant | `python3 client.py -s 192.168.56.1 -p 58000 -l 5800X` |

**Fluxo típico:**
1. Rodar servidor no Windows
2. `vagrant up` → `vagrant ssh` → `cd p2pnet`
3. Rodar cliente(s) na VM
4. `join` para entrar na rede
5. Testar comandos

---

**Pronto! 🎉** Agora você pode desenvolver e testar o projeto P2P.

Para dúvidas, consulte:
- `PROJETO_EXPLICADO.md` — Visão geral do projeto
- `WILLIAM_TESTS.md` / `BERNARDO_TESTS.md` — Testes específicos por desenvolvedor
- `TAREFAS_TODO.md` — Tarefas pendentes
