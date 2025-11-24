from typing import Tuple, Optional
from common.models import Neighbor, NeighborAddResult

def add_internal_neighbor(peer, neigh: Neighbor, isFrc: bool=False) -> Tuple[NeighborAddResult, Optional[Neighbor]]:
    """
    Tenta adicionar um vizinho interno seguindo as regras do protocolo P2P.
    """
    # 1. Verificar se já é vizinho interno (evitar duplicados)
    for existing in peer.internal_neighbors:
        if existing.ip == neigh.ip and existing.port == neigh.port:
            return (NeighborAddResult.ALREADY_NEIGHBOR, None)
    
    # 2. Se há espaço livre, aceitar diretamente
    if len(peer.internal_neighbors) < peer.args.neighMx and peer.getSeqnumber() < neigh.seqnumber:
        peer.internal_neighbors.append(neigh)
        neigh.status = "ativo"
        return (NeighborAddResult.ACCEPT, None)
    
    # 3. Tabela cheia - aplicar regras de seqnumber
    
    if isFrc:
        # 3b. Se seq_incoming < seq_self → tentar FRC
        # Procurar vizinho interno com seq > seq_incoming (candidato a ser expulso)
        candidate_to_remove: Optional[Neighbor] = None
        
        for existing in peer.internal_neighbors:
            if existing.seqnumber > neigh.seqnumber:
                # Escolher o vizinho com maior seqnumber para expulsar
                if candidate_to_remove is None or existing.seqnumber > candidate_to_remove.seqnumber:
                    candidate_to_remove = existing
        
        # Se não encontrou candidato, rejeitar
        if candidate_to_remove is None:
            return (NeighborAddResult.REJECT, None)
        
        # Expulsar o vizinho pior e adicionar o novo
        peer.internal_neighbors.remove(candidate_to_remove)
        peer.internal_neighbors.append(neigh)
        neigh.status = "ativo"
        candidate_to_remove.status = "expulso"
        
        return (NeighborAddResult.ACCEPT_WITH_REPLACEMENT, candidate_to_remove)
    
    return (NeighborAddResult.REJECT, None)

def add_external_neighbor(peer, neigh: Neighbor):
    """Adiciona um vizinho externo (sem verificações de seqnumber)"""
    # Verificar se já existe
    for existing in peer.external_neighbors:
        if existing.ip == neigh.ip and existing.port == neigh.port:
            return
    
    peer.external_neighbors.append(neigh)
    neigh.status = "ativo"

def remove_neighbor_by_seq(peer, seqnumber: int) -> Optional[Neighbor]:
    """Remove um vizinho pelo seqnumber e retorna-o se encontrado"""
    for neighbor in peer.internal_neighbors:
        if neighbor.seqnumber == seqnumber:
            peer.internal_neighbors.remove(neighbor)
            return neighbor
    
    for neighbor in peer.external_neighbors:
        if neighbor.seqnumber == seqnumber:
            peer.external_neighbors.remove(neighbor)
            return neighbor
    
    return None
