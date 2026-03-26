# Integrantes:
#   Arthur Felipe Bach Biancolini
#   Emanuel Riceto da Silva
#   Frederico Virmond Fruet
#   Pedro Alessandrini Braiti
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

from dataclasses import dataclass
from typing import List, Dict, Tuple


class ErroLexico(Exception):
    pass


@dataclass
class Token:
    tipo: str
    valor: str
    linha: int
    coluna: int


TIPO_NUMERO = "NUMERO"
TIPO_OPERADOR = "OPERADOR"
TIPO_ABRE = "PARENTESE_ABRE"
TIPO_FECHA = "PARENTESE_FECHA"
TIPO_IDENT = "IDENTIFICADOR"
TIPO_KEYWORD = "KEYWORD"


def _eh_digito(char: str) -> bool:
    return "0" <= char <= "9"


def _eh_maiuscula(char: str) -> bool:
    return "A" <= char <= "Z"


def _adicionar_token(contexto: Dict, tipo: str, valor: str) -> None:
    contexto["tokens"].append(
        Token(tipo=tipo, valor=valor, linha=contexto["linha"], coluna=contexto["inicio_token"] + 1)
    )
