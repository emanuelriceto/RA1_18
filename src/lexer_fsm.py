# Integrantes:
#   Arthur Felipe Bach Biancolini (Tuizones)
#   Emanuel Riceto da Silva (emanuelriceto)
#   Frederico Virmond Fruet (fredfruet)
#   Pedro Alessandrini Braiti (pedrobraiti)
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

# Analisador léxico usando AFD (autômato finito determinístico).
# Implementado só com funções de estado, sem usar regex.
# Cada estado do autômato é uma função que recebe um caractere e decide
# pra qual estado ir.
#
# Estados: inicial, numero, numero_decimal, identificador, barra
#
# Tokens: NUMERO, OPERADOR (+,-,*,/,//,%,^), PARENTESE_ABRE,
#         PARENTESE_FECHA, IDENTIFICADOR (nomes de memória), KEYWORD (RES)
#
# O diagrama do AFD ta no README

from dataclasses import dataclass

class Erros(Exception):
    pass

@dataclass
class Token:
    """Um token com tipo, valor e posição na linha."""
    tipo: str
    valor: str
    linha: int
    coluna: int

# Tipos de token
TIPO_NUMERO = "NUMERO"
TIPO_OPERADOR = "OPERADOR"
TIPO_ABRE = "PARENTESE_ABRE"
TIPO_FECHA = "PARENTESE_FECHA"
TIPO_IDENT = "IDENTIFICADOR"
TIPO_KEYWORD = "KEYWORD"

# Funções auxiliares pra classificar caracteres 

def _eh_digito(char: str) -> bool:
    return "0" <= char <= "9"

def _eh_maiuscula(char: str) -> bool:
    return "A" <= char <= "Z"

def _eh_minuscula(char: str) -> bool:
    return "a" <= char <= "z"

def _adicionar_token(contexto: dict, tipo: str, valor: str) -> None:
    """Cria um Token e joga na lista."""
    contexto["tokens"].append(
        Token(tipo=tipo, valor=valor, linha=contexto["linha"], coluna=contexto["inicio_token"] + 1)
    )


# Cada função recebe (caractere, contexto) e retorna (proximo_estado, avancar_cursor).
# Quando avancar=False o caractere é reprocessado no próximo estado.

def estado_inicial(char: str, contexto: dict) -> tuple[str, bool]:
    """Classifica o caractere e decide pra qual estado ir."""
    # ignora espaços
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

    # digito -> vai pro estado numero
    if _eh_digito(char):
        contexto["buffer"] = char
        contexto["inicio_token"] = contexto["i"]
        return "numero", True

    # letra maiuscula -> identificador (MEM, RES, etc)
    if _eh_maiuscula(char):
        contexto["buffer"] = char
        contexto["inicio_token"] = contexto["i"]
        return "identificador", True

    # operadores simples
    if char in "+-*%^":
        contexto["inicio_token"] = contexto["i"]
        _adicionar_token(contexto, TIPO_OPERADOR, char)
        return "inicial", True

    # barra: pode ser / ou //
    if char == "/":
        contexto["buffer"] = "/"
        contexto["inicio_token"] = contexto["i"]
        return "barra", True

    # ponto solto sem digito antes (tipo .5)
    if char == ".":
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: número malformado — ponto sem dígito antes"
        )

    # minuscula nao pode
    if _eh_minuscula(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: identificadores devem usar apenas letras maiúsculas, encontrado '{char}'"
        )

    # caractere invalido
    raise Erros(f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: caractere inválido '{char}'")


def estado_numero(char: str, contexto: dict) -> tuple[str, bool]:
    """Acumula dígitos. Se encontrar ponto vai pra decimal."""
    # mais digitos
    if _eh_digito(char):
        contexto["buffer"] += char
        return "numero", True

    # achou ponto, vira decimal
    if char == ".":
        contexto["buffer"] += char
        return "numero_decimal", True

    # letra grudada no numero = erro
    if _eh_maiuscula(char) or _eh_minuscula(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"número malformado '{contexto['buffer'] + char}' — letra imediatamente após número"
        )

    # qualquer outra coisa: emite o numero e reprocessa o char
    _adicionar_token(contexto, TIPO_NUMERO, contexto["buffer"])
    contexto["buffer"] = ""
    return "inicial", False


def estado_numero_decimal(char: str, contexto: dict) -> tuple[str, bool]:
    """Acumula dígitos da parte decimal (após o ponto)."""
    if _eh_digito(char):
        contexto["buffer"] += char
        return "numero_decimal", True

    # dois pontos (tipo 3.14.5)
    if char == ".":
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"número malformado '{contexto['buffer'] + char}' — múltiplos pontos decimais"
        )

    # ponto sem nada depois (tipo 3.)
    if contexto["buffer"].endswith("."):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i']}: "
            f"número malformado '{contexto['buffer']}' — ponto decimal sem dígitos depois"
        )

    # letra grudada (tipo 2.0a)
    if _eh_maiuscula(char) or _eh_minuscula(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"número malformado '{contexto['buffer'] + char}' — letra imediatamente após número"
        )

    # numero completo, emite e volta
    _adicionar_token(contexto, TIPO_NUMERO, contexto["buffer"])
    contexto["buffer"] = ""
    return "inicial", False


def estado_identificador(char: str, contexto: dict) -> tuple[str, bool]:
    """Acumula letras maiúsculas. Diferencia RES (keyword) de nomes de memória."""
    if _eh_maiuscula(char):
        contexto["buffer"] += char
        return "identificador", True

    # minuscula misturada = erro
    if _eh_minuscula(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"identificador '{contexto['buffer'] + char}' contém letra minúscula — use apenas maiúsculas"
        )

    # numero no identificador = erro
    if _eh_digito(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"identificador '{contexto['buffer'] + char}' contém dígito — use apenas letras maiúsculas"
        )

    # terminou: se for "RES" é keyword, senão é nome de memória
    valor = contexto["buffer"]
    if valor == "RES":
        _adicionar_token(contexto, TIPO_KEYWORD, valor)
    else:
        _adicionar_token(contexto, TIPO_IDENT, valor)

    contexto["buffer"] = ""
    return "inicial", False


def estado_barra(char: str, contexto: dict) -> tuple[str, bool]:
    """Diferencia / (divisão real) de // (divisão inteira)."""
    # segunda barra -> //
    if char == "/":
        _adicionar_token(contexto, TIPO_OPERADOR, "//")
        contexto["buffer"] = ""
        return "inicial", True

    # só uma barra -> /
    _adicionar_token(contexto, TIPO_OPERADOR, "/")
    contexto["buffer"] = ""
    return "inicial", False


def _finalizar(contexto: dict, estado: str) -> None:
    """Emite token pendente no buffer e checa se os parênteses fecharam certo."""
    # emite o que tiver pendente no buffer
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

    # checa parenteses
    if contexto["paren"] != 0:
        raise Erros(f"Linha {contexto['linha']}: parênteses desbalanceados")


def tokenizar_linha(linha: str, numero_linha: int = 1) -> list[Token]:
    """Tokeniza uma linha de expressão RPN usando o AFD.
    Retorna lista de Tokens ou levanta Erros se a entrada for inválida.
    """
    # contexto compartilhado entre os estados
    contexto = {
        "tokens": [],
        "buffer": "",
        "i": 0,
        "inicio_token": 0,
        "linha": numero_linha,
        "paren": 0,
    }

    estado = "inicial"

    # mapeia nome do estado -> função
    maquina = {
        "inicial": estado_inicial,
        "numero": estado_numero,
        "numero_decimal": estado_numero_decimal,
        "identificador": estado_identificador,
        "barra": estado_barra,
    }

    # coloca \n no final pra garantir que o ultimo token seja emitido
    chars = linha + "\n"
    # loop principal: consome caractere a caractere
    while contexto["i"] < len(chars):
        char = chars[contexto["i"]]
        proximo_estado, avancar = maquina[estado](char, contexto)
        estado = proximo_estado
        if avancar:
            contexto["i"] += 1

    _finalizar(contexto, estado)
    return contexto["tokens"]
