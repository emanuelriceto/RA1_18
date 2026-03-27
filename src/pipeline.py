# Integrantes:
#   Arthur Felipe Bach Biancolini
#   Emanuel Riceto da Silva
#   Frederico Virmond Fruet
#   Pedro Alessandrini Braiti
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

from typing import Dict, List, Tuple, Any

from .lexer_fsm import (
    Token,
    ErroLexico,
    TIPO_ABRE,
    TIPO_FECHA,
    TIPO_IDENT,
    TIPO_KEYWORD,
    TIPO_NUMERO,
    TIPO_OPERADOR,
    tokenizar_linha,
)
from .armv7_generator import gerar_assembly_armv7


class ErroSintaxe(Exception):
    pass


class ErroExecucao(Exception):
    pass


def parseExpressao(linha: str, tokens_saida: List[str]) -> List[Token]:
    tokens = tokenizar_linha(linha)
    tokens_saida.extend(token.valor for token in tokens)
    return tokens


def _eh_numero_inteiro_literal(valor: str) -> bool:
    for ch in valor:
        if ch < "0" or ch > "9":
            return False
    return len(valor) > 0


def _parse_item(tokens: List[Token], i: int) -> Tuple[Dict[str, Any], int]:
    if i >= len(tokens):
        raise ErroSintaxe("Fim inesperado de expressão")

    token = tokens[i]
    if token.tipo == TIPO_ABRE:
        return _parse_expr(tokens, i)

    if token.tipo == TIPO_NUMERO:
        return {"tipo": "number", "valor": token.valor}, i + 1

    if token.tipo == TIPO_IDENT:
        return {"tipo": "ident", "valor": token.valor}, i + 1

    if token.tipo == TIPO_KEYWORD:
        return {"tipo": "keyword", "valor": token.valor}, i + 1

    raise ErroSintaxe(f"Token inesperado: {token.valor}")


def _parse_expr(tokens: List[Token], i: int) -> Tuple[Dict[str, Any], int]:
    if tokens[i].tipo != TIPO_ABRE:
        raise ErroSintaxe("Expressão deve iniciar com '('")

    i += 1
    primeiro, i = _parse_item(tokens, i)

    if i >= len(tokens):
        raise ErroSintaxe("Fim inesperado após primeiro item")

    if tokens[i].tipo == TIPO_FECHA:
        i += 1
        if primeiro["tipo"] != "ident":
            raise ErroSintaxe("Comando (MEM) exige identificador em letras maiúsculas")
        return {"tipo": "mem_read", "nome": primeiro["valor"]}, i

    segundo, i = _parse_item(tokens, i)

    if i >= len(tokens):
        raise ErroSintaxe("Fim inesperado após segundo item")

    if tokens[i].tipo == TIPO_FECHA:
        i += 1
        if segundo.get("tipo") == "keyword" and segundo.get("valor") == "RES":
            if primeiro.get("tipo") != "number" or not _eh_numero_inteiro_literal(primeiro.get("valor", "")):
                raise ErroSintaxe("Comando (N RES) exige N inteiro não negativo")
            return {"tipo": "res_ref", "linhas_atras": int(primeiro["valor"])}, i

        if segundo.get("tipo") == "ident":
            return {"tipo": "mem_write", "nome": segundo["valor"], "valor": primeiro}, i

        raise ErroSintaxe("Expressão de dois itens inválida")

    op = tokens[i]
    if op.tipo != TIPO_OPERADOR:
        raise ErroSintaxe(f"Operador esperado, encontrado: {op.valor}")

    i += 1
    if i >= len(tokens) or tokens[i].tipo != TIPO_FECHA:
        raise ErroSintaxe("')' esperado ao final da expressão")

    i += 1
    return {"tipo": "binary", "op": op.valor, "esq": primeiro, "dir": segundo}, i


def _arvore_de_tokens(tokens: List[Token]) -> Dict[str, Any]:
    arvore, i = _parse_expr(tokens, 0)
    if i != len(tokens):
        raise ErroSintaxe("Tokens extras após o fim da expressão")
    return arvore


def executarExpressao(tokens: List[Token], contexto: Dict[str, Any]) -> Dict[str, Any]:
    arvore = _arvore_de_tokens(tokens)

    if "memoria" not in contexto:
        contexto["memoria"] = {}
    if "resultados" not in contexto:
        contexto["resultados"] = []

    tipo = arvore["tipo"]
    descricao = "expressão válida"

    if tipo == "mem_write":
        contexto["memoria"][arvore["nome"]] = "definida"
        descricao = f"memória {arvore['nome']} marcada como definida"
    elif tipo == "mem_read":
        if arvore["nome"] not in contexto["memoria"]:
            contexto["memoria"][arvore["nome"]] = "não inicializada"
        descricao = f"leitura da memória {arvore['nome']}"
    elif tipo == "res_ref":
        n = arvore["linhas_atras"]
        if n > len(contexto["resultados"]):
            raise ErroExecucao(f"RES inválido: {n} linhas atrás não disponível")
        descricao = f"referência ao resultado de {n} linhas atrás"

    contexto["resultados"].append("gerado_em_assembly")
    return {"ok": True, "descricao": descricao, "arvore": arvore}


def gerarAssembly(tokens_por_linha: List[List[Token]], codigoAssembly: str = "") -> str:
    arvores = [_arvore_de_tokens(tokens) for tokens in tokens_por_linha]
    return gerar_assembly_armv7(arvores)


def exibirResultados(resultados: List[Dict[str, Any]]) -> None:
    for i, resultado in enumerate(resultados, start=1):
        print(f"Linha {i}: {resultado['descricao']}")


def lerArquivo(nomeArquivo: str, linhas: List[str]) -> None:
    import os
    if not os.path.isfile(nomeArquivo):
        alternativo = os.path.join("exemplos", nomeArquivo)
        if os.path.isfile(alternativo):
            nomeArquivo = alternativo
    with open(nomeArquivo, "r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            texto = linha.strip()
            if texto and not texto.startswith("#"):
                linhas.append(texto)
