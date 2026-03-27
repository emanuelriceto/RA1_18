# Integrantes:
#   Arthur Felipe Bach Biancolini
#   Emanuel Riceto da Silva
#   Frederico Virmond Fruet
#   Pedro Alessandrini Braiti
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

from typing import Dict, List, Tuple, Set


def _normalizar_nome_mem(nome: str) -> str:
    return nome.lower()


def _coletar_memorias(no: Dict, memorias: Set[str]) -> None:
    tipo = no["tipo"]
    if tipo == "mem_write":
        memorias.add(_normalizar_nome_mem(no["nome"]))
        _coletar_memorias(no["valor"], memorias)
    elif tipo == "mem_read":
        memorias.add(_normalizar_nome_mem(no["nome"]))
    elif tipo == "binary":
        _coletar_memorias(no["esq"], memorias)
        _coletar_memorias(no["dir"], memorias)


def _emit_push_d0(linhas: List[str]) -> None:
    linhas.append("    VMOV r4, r5, d0")
    linhas.append("    PUSH {r4, r5}")


def _emit_pop_para_d(linhas: List[str], reg_d: str) -> None:
    linhas.append("    POP {r4, r5}")
    linhas.append(f"    VMOV {reg_d}, r4, r5")
