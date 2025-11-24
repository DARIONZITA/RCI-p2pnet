from enum import Enum

class NeighborAddResult(Enum):
    """Resultado da tentativa de adicionar um vizinho interno"""
    ACCEPT = "accept"                           # Aceite direto (há espaço)
    REJECT = "reject"                           # Rejeitado (seq maior que o próprio ou sem candidato a FRC)
    ACCEPT_WITH_REPLACEMENT = "accept_frc"      # Aceite via FRC (expulsar vizinho pior)
    ALREADY_NEIGHBOR = "already"                # Já é vizinho (evitar duplicados)

class Neighbor:
    def __init__(self, ip, port, seqnumber, socket_fd=None, status="pendente"):
        self.ip = ip
        self.port = port
        self.seqnumber = seqnumber
        self.socket_fd = socket_fd
        self.status = status

class Identifier:
    def __init__(self):
        self.identificadores = []
    
    def addIdentifier(self, identifier):
        self.identificadores.append(identifier)
    
    def removeIdentifier(self, identifier):
        self.identificadores.remove(identifier)
    
    def hasIdentifier(self, identifier):
        return identifier in self.identificadores
    
    def listIdentifiers(self):
        return self.identificadores

class QueryState:
    def __init__(self, requester_socket, identifier, pending_count):
        self.requester_socket = requester_socket
        self.identifier = identifier
        self.pending_count = pending_count
