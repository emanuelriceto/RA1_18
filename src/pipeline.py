# Integrantes:
#   Arthur Felipe Bach Biancolini (Tuizones)
#   Emanuel Riceto da Silva (emanuelriceto)
#   Frederico Virmond Fruet (fredfruet)
#   Pedro Alessandrini Braiti (pedrobraiti)
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

# 5 funções obrigatórias do pipeline:
# parseExpressao, executarExpressao, gerarAssembly, exibirResultados, lerArquivo

from .lexer_fsm import (
    Token,
    Erros,
    TIPO_ABRE,
    TIPO_FECHA,
    TIPO_IDENT,
    TIPO_KEYWORD,
    TIPO_NUMERO,
    TIPO_OPERADOR,
    tokenizar_linha,
)
from .armv7_generator import gerar_assembly_armv7

# Tokeniza uma linha usando o AFD do lexer

def parseExpressao(linha: str, tokens_saida: list[str]) -> list[Token]:
    """Recebe uma linha RPN, roda o AFD e retorna os tokens."""
    tokens = tokenizar_linha(linha)
    tokens_saida.extend(token.valor for token in tokens)
    return tokens

# Parser recursivo que monta a AST a partir dos tokens.
# A AST depois é usada pra validar e gerar o Assembly.

def _eh_numero_inteiro_literal(valor: str) -> bool:
    """Checa se é um inteiro não-negativo (pra usar no N RES)."""
    for ch in valor:
        if ch < "0" or ch > "9":
            return False
    return len(valor) > 0


def _parse_item(tokens: list[Token], i: int) -> tuple[dict[str, any], int]:
    """Parseia um item: numero, identificador, keyword ou sub-expressão."""
    if i >= len(tokens):
        raise Erros("Fim inesperado de expressão")

    token = tokens[i]
    # sub-expressao entre parenteses -> recursao
    if token.tipo == TIPO_ABRE:
        return _parse_expr(tokens, i)

    # Numero
    if token.tipo == TIPO_NUMERO:
        return {"tipo": "number", "valor": token.valor}, i + 1

    # Identificador (nome de memória tipo MEM, VARA, etc)
    if token.tipo == TIPO_IDENT:
        return {"tipo": "ident", "valor": token.valor}, i + 1

    # Keyword (só tem RES por enquanto)
    if token.tipo == TIPO_KEYWORD:
        return {"tipo": "keyword", "valor": token.valor}, i + 1

    raise Erros(f"Token inesperado: {token.valor}")


def _parse_expr(tokens: list[Token], i: int) -> tuple[dict[str, any], int]:
    """Parseia uma expressão RPN: (A B op), (MEM), (V MEM) ou (N RES)."""
    if tokens[i].tipo != TIPO_ABRE:
        raise Erros("Expressão deve iniciar com '('")

    i += 1
    primeiro, i = _parse_item(tokens, i)

    if i >= len(tokens):
        raise Erros("Fim inesperado após primeiro item")

    # (MEM) - leitura de memória
    if tokens[i].tipo == TIPO_FECHA:
        i += 1
        if primeiro["tipo"] != "ident":
            raise Erros("Comando (MEM) exige identificador em letras maiúsculas")
        return {"tipo": "mem_read", "nome": primeiro["valor"]}, i

    segundo, i = _parse_item(tokens, i)

    if i >= len(tokens):
        raise Erros("Fim inesperado após segundo item")

    # dois itens seguidos de ')'
    if tokens[i].tipo == TIPO_FECHA:
        i += 1
        # (N RES)
        if segundo.get("tipo") == "keyword" and segundo.get("valor") == "RES":
            if primeiro.get("tipo") != "number" or not _eh_numero_inteiro_literal(primeiro.get("valor", "")):
                raise Erros("Comando (N RES) exige N inteiro não negativo")
            return {"tipo": "res_ref", "linhas_atras": int(primeiro["valor"])}, i

        # (V MEM) - escrita em memória
        if segundo.get("tipo") == "ident":
            return {"tipo": "mem_write", "nome": segundo["valor"], "valor": primeiro}, i

        raise Erros("Expressão de dois itens inválida")

    # (A B op) - operação binária
    op = tokens[i]
    if op.tipo != TIPO_OPERADOR:
        raise Erros(f"Operador esperado, encontrado: {op.valor}")

    i += 1
    if i >= len(tokens) or tokens[i].tipo != TIPO_FECHA:
        raise Erros("')' esperado ao final da expressão")

    i += 1
    return {"tipo": "binary", "op": op.valor, "esq": primeiro, "dir": segundo}, i


def _arvore_de_tokens(tokens: list[Token]) -> dict[str, any]:
    """Monta a AST e valida que não sobrou token."""
    arvore, i = _parse_expr(tokens, 0)
    if i != len(tokens):
        raise Erros("Tokens extras após o fim da expressão")
    return arvore


# Valida semantica sem fazer nenhum calculo (os calculos são feitos no Assembly)


def executarExpressao(tokens: list[Token], contexto: dict[str, any]) -> dict[str, any]:
    """Valida a expressão: checa MEM, RES, e monta a AST.
    Nenhum cálculo é feito aqui, só no Assembly.
    """
    arvore = _arvore_de_tokens(tokens)

    if "memoria" not in contexto:
        contexto["memoria"] = {}
    if "resultados" not in contexto:
        contexto["resultados"] = []

    tipo = arvore["tipo"]
    descricao = "expressão válida"

    # escrita em memoria
    if tipo == "mem_write":
        contexto["memoria"][arvore["nome"]] = "definida"
        descricao = f"memória {arvore['nome']} marcada como definida"
    # leitura de memoria
    elif tipo == "mem_read":
        if arvore["nome"] not in contexto["memoria"]:
            contexto["memoria"][arvore["nome"]] = "não inicializada"
        descricao = f"leitura da memória {arvore['nome']}"
    # referencia a resultado anterior
    elif tipo == "res_ref":
        n = arvore["linhas_atras"]
        if n > len(contexto["resultados"]):
            raise Erros(f"RES inválido: {n} linhas atrás não disponível")
        descricao = f"referência ao resultado de {n} linhas atrás"

    # registra que essa linha vai ter um resultado
    contexto["resultados"].append("gerado_em_assembly")
    return {"ok": True, "descricao": descricao, "arvore": arvore}

# Gera o Assembly ARMv7 a partir dos tokens

def gerarAssembly(tokens_por_linha: list[list[Token]], codigoAssembly: str = "") -> str:
    """Monta as ASTs e chama o gerador de Assembly ARMv7."""
    # monta AST de cada linha e manda pro gerador
    arvores = [_arvore_de_tokens(tokens) for tokens in tokens_por_linha]
    return gerar_assembly_armv7(arvores)

# Exibe resultados no console

def exibirResultados(resultados: list[dict[str, any]]) -> None:
    """Printa a descrição de cada expressão processada."""
    for i, resultado in enumerate(resultados, start=1):
        print(f"Linha {i}: {resultado['descricao']}")

# Lê o arquivo de teste

def lerArquivo(nomeArquivo: str, linhas: list[str]) -> None:
    """Lê o arquivo RPN ignorando linhas vazias e comentários (#)."""
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
