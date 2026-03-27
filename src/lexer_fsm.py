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


class Erros(Exception):
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


def _eh_minuscula(char: str) -> bool:
    return "a" <= char <= "z"


def _adicionar_token(contexto: Dict, tipo: str, valor: str) -> None:
    contexto["tokens"].append(
        Token(tipo=tipo, valor=valor, linha=contexto["linha"], coluna=contexto["inicio_token"] + 1)
    )


def estado_inicial(char: str, contexto: Dict) -> Tuple[str, bool]:
    if char in (" ", "\t", "\r", "\n"):
        return "inicial", True

    if char == "(":
        contexto["inicio_token"] = contexto["i"]
        _adicionar_token(contexto, TIPO_ABRE, "(")
        contexto["paren"] += 1
        return "inicial", True

    if char == ")":
        contexto["inicio_token"] = contexto["i"]
        if contexto["paren"] <= 0:
            raise Erros(f"Linha {contexto['linha']}: ')' sem '(' correspondente")
        contexto["paren"] -= 1
        _adicionar_token(contexto, TIPO_FECHA, ")")
        return "inicial", True

    if _eh_digito(char):
        contexto["buffer"] = char
        contexto["inicio_token"] = contexto["i"]
        return "numero", True

    if _eh_maiuscula(char):
        contexto["buffer"] = char
        contexto["inicio_token"] = contexto["i"]
        return "identificador", True

    if char in "+-*%^":
        contexto["inicio_token"] = contexto["i"]
        _adicionar_token(contexto, TIPO_OPERADOR, char)
        return "inicial", True

    if char == "/":
        contexto["buffer"] = "/"
        contexto["inicio_token"] = contexto["i"]
        return "barra", True

    if char == ".":
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: número malformado — ponto sem dígito antes"
        )

    if _eh_minuscula(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: identificadores devem usar apenas letras maiúsculas, encontrado '{char}'"
        )

    raise Erros(f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: caractere inválido '{char}'")


def estado_numero(char: str, contexto: Dict) -> Tuple[str, bool]:
    if _eh_digito(char):
        contexto["buffer"] += char
        return "numero", True

    if char == ".":
        contexto["buffer"] += char
        return "numero_decimal", True

    if _eh_maiuscula(char) or _eh_minuscula(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"número malformado '{contexto['buffer'] + char}' — letra imediatamente após número"
        )

    _adicionar_token(contexto, TIPO_NUMERO, contexto["buffer"])
    contexto["buffer"] = ""
    return "inicial", False


def estado_numero_decimal(char: str, contexto: Dict) -> Tuple[str, bool]:
    if _eh_digito(char):
        contexto["buffer"] += char
        return "numero_decimal", True

    if char == ".":
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"número malformado '{contexto['buffer'] + char}' — múltiplos pontos decimais"
        )

    if contexto["buffer"].endswith("."):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i']}: "
            f"número malformado '{contexto['buffer']}' — ponto decimal sem dígitos depois"
        )

    if _eh_maiuscula(char) or _eh_minuscula(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"número malformado '{contexto['buffer'] + char}' — letra imediatamente após número"
        )

    _adicionar_token(contexto, TIPO_NUMERO, contexto["buffer"])
    contexto["buffer"] = ""
    return "inicial", False


def estado_identificador(char: str, contexto: Dict) -> Tuple[str, bool]:
    if _eh_maiuscula(char):
        contexto["buffer"] += char
        return "identificador", True

    if _eh_minuscula(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"identificador '{contexto['buffer'] + char}' contém letra minúscula — use apenas maiúsculas"
        )

    if _eh_digito(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"identificador '{contexto['buffer'] + char}' contém dígito — use apenas letras maiúsculas"
        )

    valor = contexto["buffer"]
    if valor == "RES":
        _adicionar_token(contexto, TIPO_KEYWORD, valor)
    else:
        _adicionar_token(contexto, TIPO_IDENT, valor)

    contexto["buffer"] = ""
    return "inicial", False


def estado_barra(char: str, contexto: Dict) -> Tuple[str, bool]:
    if char == "/":
        _adicionar_token(contexto, TIPO_OPERADOR, "//")
        contexto["buffer"] = ""
        return "inicial", True

    _adicionar_token(contexto, TIPO_OPERADOR, "/")
    contexto["buffer"] = ""
    return "inicial", False


def _finalizar(contexto: Dict, estado: str) -> None:
    if estado == "numero":
        _adicionar_token(contexto, TIPO_NUMERO, contexto["buffer"])
    elif estado == "numero_decimal":
        if contexto["buffer"].endswith("."):
            raise Erros(f"Linha {contexto['linha']}: número malformado '{contexto['buffer']}'")
        _adicionar_token(contexto, TIPO_NUMERO, contexto["buffer"])
    elif estado == "identificador":
        valor = contexto["buffer"]
        if valor == "RES":
            _adicionar_token(contexto, TIPO_KEYWORD, valor)
        else:
            _adicionar_token(contexto, TIPO_IDENT, valor)
    elif estado == "barra":
        _adicionar_token(contexto, TIPO_OPERADOR, "/")

    if contexto["paren"] != 0:
        raise Erros(f"Linha {contexto['linha']}: parênteses desbalanceados")


def tokenizar_linha(linha: str, numero_linha: int = 1) -> List[Token]:
    contexto = {
        "tokens": [],
        "buffer": "",
        "i": 0,
        "inicio_token": 0,
        "linha": numero_linha,
        "paren": 0,
    }

    estado = "inicial"
    maquina = {
        "inicial": estado_inicial,
        "numero": estado_numero,
        "numero_decimal": estado_numero_decimal,
        "identificador": estado_identificador,
        "barra": estado_barra,
    }

    chars = linha + "\n"
    while contexto["i"] < len(chars):
        char = chars[contexto["i"]]
        proximo_estado, avancar = maquina[estado](char, contexto)
        estado = proximo_estado
        if avancar:
            contexto["i"] += 1

    _finalizar(contexto, estado)
    return contexto["tokens"]
