# Integrantes:
#   Arthur Felipe Bach Biancolini (Tuizones)
#   Emanuel Riceto da Silva (emanuelriceto)
#   Frederico Virmond Fruet (fredfruet)
#   Pedro Alessandrini Braiti (pedrobraiti)
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

from typing import Dict, List, Tuple, Any

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


# Interface: recebe uma linha de texto e retorna um vetor de tokens.
# Usa o AFD de lexer_fsm.py (sem regex) para tokenização.

def parseExpressao(linha: str, tokens_saida: List[str]) -> List[Token]:
    """Analisa uma linha de expressão RPN e extrai tokens via AFD.

    Recebe uma linha de texto, faz análise léxica
    usando o Autômato Finito Determinístico (tokenizar_linha), e retorna
    o vetor de tokens. Também popula tokens_saida com os valores em string.

    Args:
        linha         — string contendo uma expressão RPN (ex.: '(3.14 2.0 +)')
        tokens_saida  — lista que será preenchida com os valores dos tokens

    Returns:
        Lista de objetos Token gerados pelo AFD.
    """
    tokens = tokenizar_linha(linha)
    tokens_saida.extend(token.valor for token in tokens)
    return tokens

# Parser recursivo descendente — constrói a Árvore Sintática Abstrata (AST)
# a partir do vetor de tokens gerado pelo AFD.
# A AST é utilizada internamente para validação semântica e para a geração
# de código Assembly

def _eh_numero_inteiro_literal(valor: str) -> bool:
    """Verifica se a string representa um inteiro não negativo (para N RES)."""
    for ch in valor:
        if ch < "0" or ch > "9":
            return False
    return len(valor) > 0


def _parse_item(tokens: List[Token], i: int) -> Tuple[Dict[str, Any], int]:
    """Analisa um item individual da expressão RPN: número, identificador,
    keyword ou sub-expressão entre parênteses (aninhamento sem limites)."""
    if i >= len(tokens):
        raise Erros("Fim inesperado de expressão")

    token = tokens[i]
    # Sub-expressão aninhada — recursão para expressões como ((A B +) C *)
    if token.tipo == TIPO_ABRE:
        return _parse_expr(tokens, i)

    # Número real IEEE 754 64 bits (ex.: 3.14, 42)
    if token.tipo == TIPO_NUMERO:
        return {"tipo": "number", "valor": token.valor}, i + 1

    # Identificador — nome de memória em maiúsculas (ex.: MEM, VARA, TEMP)
    if token.tipo == TIPO_IDENT:
        return {"tipo": "ident", "valor": token.valor}, i + 1

    # Keyword — RES (única keyword da Fase 1)
    if token.tipo == TIPO_KEYWORD:
        return {"tipo": "keyword", "valor": token.valor}, i + 1

    raise Erros(f"Token inesperado: {token.valor}")


def _parse_expr(tokens: List[Token], i: int) -> Tuple[Dict[str, Any], int]:
    """Analisa uma expressão RPN completa no formato (A B op).

    Reconhece os seguintes formatos:
        (A B op)    — operação binária: +, -, *, /, //, %, ^
        (MEM)       — leitura de memória (retorna valor armazenado)
        (V MEM)     — escrita de valor em memória
        (N RES)     — referência ao resultado de N linhas anteriores
        Expressões aninhadas: ((A B +) (C D *) /) sem limite de profundidade
    """
    if tokens[i].tipo != TIPO_ABRE:
        raise Erros("Expressão deve iniciar com '('")

    i += 1  # Avança após '('
    primeiro, i = _parse_item(tokens, i)

    if i >= len(tokens):
        raise Erros("Fim inesperado após primeiro item")

    # Formato (MEM) — leitura de memória
    # Se logo após o primeiro item vem ')', é uma leitura de memória
    if tokens[i].tipo == TIPO_FECHA:
        i += 1
        if primeiro["tipo"] != "ident":
            raise Erros("Comando (MEM) exige identificador em letras maiúsculas")
        return {"tipo": "mem_read", "nome": primeiro["valor"]}, i

    segundo, i = _parse_item(tokens, i)

    if i >= len(tokens):
        raise Erros("Fim inesperado após segundo item")

    # Formato com dois itens seguido de ')'
    if tokens[i].tipo == TIPO_FECHA:
        i += 1
        # (N RES) — referência a resultado anterior
        # N deve ser inteiro não negativo
        if segundo.get("tipo") == "keyword" and segundo.get("valor") == "RES":
            if primeiro.get("tipo") != "number" or not _eh_numero_inteiro_literal(primeiro.get("valor", "")):
                raise Erros("Comando (N RES) exige N inteiro não negativo")
            return {"tipo": "res_ref", "linhas_atras": int(primeiro["valor"])}, i

        # (V MEM) — escrita em memória
        # V é o valor e MEM é um identificador em maiúsculas
        if segundo.get("tipo") == "ident":
            return {"tipo": "mem_write", "nome": segundo["valor"], "valor": primeiro}, i

        raise Erros("Expressão de dois itens inválida")

    # Formato (A B op) — operação binária
    # Operadores suportados: +, -, *, /, //, %, ^
    op = tokens[i]
    if op.tipo != TIPO_OPERADOR:
        raise Erros(f"Operador esperado, encontrado: {op.valor}")

    i += 1  # Avança após operador
    if i >= len(tokens) or tokens[i].tipo != TIPO_FECHA:
        raise Erros("')' esperado ao final da expressão")

    i += 1  # Avança após ')'
    # Retorna nó binário da AST com operandos esquerdo, direito e operador
    return {"tipo": "binary", "op": op.valor, "esq": primeiro, "dir": segundo}, i


def _arvore_de_tokens(tokens: List[Token]) -> Dict[str, Any]:
    """Converte a lista de tokens em árvore sintática abstrata (AST).
    Valida que não sobram tokens após o parsing da expressão."""
    arvore, i = _parse_expr(tokens, 0)
    if i != len(tokens):
        raise Erros("Tokens extras após o fim da expressão")
    return arvore


# Interface: recebe tokens de parseExpressao e valida semanticamente.
# IMPORTANTE: nenhum cálculo é realizado aqui.
# Os cálculos são delegados ao código Assembly ARMv7 gerado.


def executarExpressao(tokens: List[Token], contexto: Dict[str, Any]) -> Dict[str, Any]:
    """Processa tokens e valida a semântica da expressão.

    Gerencia memória MEM para comandos (V MEM) e (MEM),
    mantém histórico de resultados para (N RES), e valida referências.

    NOTA: Nenhum cálculo é realizado em Python. O código
    Assembly gerado é que realiza os cálculos no CPUlator ARMv7 DE1-SoC.
    Esta função apenas valida e registra metadados para geração do Assembly.

    Args:
        tokens   — lista de Token gerada por parseExpressao
        contexto — dicionário compartilhado entre linhas com 'memoria' e 'resultados'

    Returns:
        Dicionário com status, descrição e árvore AST da expressão.
    """
    arvore = _arvore_de_tokens(tokens)

    # Inicializa estruturas de contexto se necessário
    if "memoria" not in contexto:
        contexto["memoria"] = {}  # Dicionário para variáveis MEM
    if "resultados" not in contexto:
        contexto["resultados"] = []  # Histórico para comando RES

    tipo = arvore["tipo"]
    descricao = "expressão válida"

    # (V MEM) — escrita em memória: registra variável como definida
    if tipo == "mem_write":
        contexto["memoria"][arvore["nome"]] = "definida"
        descricao = f"memória {arvore['nome']} marcada como definida"
    # (MEM) — leitura de memória: verifica existência
    elif tipo == "mem_read":
        if arvore["nome"] not in contexto["memoria"]:
            contexto["memoria"][arvore["nome"]] = "não inicializada"
        descricao = f"leitura da memória {arvore['nome']}"
    # (N RES) — referência a resultado anterior: valida alcançabilidade
    elif tipo == "res_ref":
        n = arvore["linhas_atras"]
        if n > len(contexto["resultados"]):
            raise Erros(f"RES inválido: {n} linhas atrás não disponível")
        descricao = f"referência ao resultado de {n} linhas atrás"

    # Registra que esta linha produzirá um resultado (calculado em Assembly)
    contexto["resultados"].append("gerado_em_assembly")
    return {"ok": True, "descricao": descricao, "arvore": arvore}

# Gera código Assembly ARMv7 compatível com CPUlator DE1-SoC v16.1.
# O Assembly gerado realiza TODOS os cálculos (IEEE 754 64 bits).

def gerarAssembly(tokens_por_linha: List[List[Token]], codigoAssembly: str = "") -> str:
    """Gera código Assembly ARMv7 a partir dos vetores de tokens.

    Recebe o vetor de tokens gerado pelo analisador
    léxico e traduz para Assembly ARMv7 funcional para o CPUlator DE1-SoC.
    O código Assembly gerado contém todas as operações do arquivo de teste
    e usa ponto flutuante IEEE 754 de 64 bits (.double, FPU VFPv3).

    Args:
        tokens_por_linha — lista de listas de Token (uma por linha do arquivo)
        codigoAssembly   — parâmetro de interface (não utilizado)

    Returns:
        String com o código Assembly ARMv7 completo e funcional.
    """
    # Constrói AST de cada linha e delega ao gerador de Assembly
    arvores = [_arvore_de_tokens(tokens) for tokens in tokens_por_linha]
    return gerar_assembly_armv7(arvores)

# Exibe os resultados das expressões processadas no console.

def exibirResultados(resultados: List[Dict[str, Any]]) -> None:
    """Exibe os resultados das expressões no console.

    Exibe resultados com formato claro.
    O cálculo real é feito no Assembly/CPUlator; aqui exibe-se
    a descrição semântica de cada expressão processada.
    """
    for i, resultado in enumerate(resultados, start=1):
        print(f"Linha {i}: {resultado['descricao']}")

# Lê o arquivo de texto com expressões RPN (uma por linha).

def lerArquivo(nomeArquivo: str, linhas: List[str]) -> None:
    """Lê o arquivo de entrada com expressões RPN.

    Lê um arquivo de texto contendo
    expressões aritméticas em RPN, uma por linha. Ignora:
        - Linhas em branco
        - Linhas iniciadas com '#' (comentários)

    O arquivo é processado via argumento de linha de comando,
    sem menu ou seleção interativa.

    Args:
        nomeArquivo — caminho do arquivo de teste (ex.: teste1.txt)
        linhas      — lista que será preenchida com as linhas válidas
    """
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
