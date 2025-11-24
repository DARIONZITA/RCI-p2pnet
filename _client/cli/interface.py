import sys
from logic import handlers

def handle_cli_command(peer, line):
    parts = line.strip().split()
    if not parts:
        return
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd == "join":
        handlers.handle_join(peer, args)
    elif cmd == "leave":
        handlers.handle_leave(peer, args)
    elif cmd == "show" and args and args[0] == "neighbors":
        handlers.handle_show_neighbors(peer, args)
    elif cmd == "release" and args:
        handlers.handle_release(peer, args)
    elif cmd == "post" and args:
        handlers.handle_post(peer, args)
    elif cmd == "unpost" and args:
        handlers.handle_unpost(peer, args)
    elif cmd == "list" and args and args[0] == "identifiers":
        handlers.handle_list_identifiers(peer, args)
    elif cmd == "search" and args:
        handlers.handle_search(peer, args)
    elif cmd == "exit":
        # TODO: Melhorar EXIT - William
        # 1) Chamar handlers.handle_leave(peer, []) para desregistrar primeiro
        # 2) Aguardar um pouco (time.sleep(0.5)) para mensagens serem enviadas
        # 3) Fechar sockets principais (peer.client_socket_tcp, peer.client_socket_udp)
        # 4) Usar sys.exit(0) para encerrar
        sys.exit(0)
    else:
        print("Comando não reconhecido")
