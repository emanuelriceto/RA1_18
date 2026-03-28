# Integrantes:
#   Arthur Felipe Bach Biancolini (Tuizones)
#   Emanuel Riceto da Silva (emanuelriceto)
#   Frederico Virmond Fruet (fredfruet)
#   Pedro Alessandrini Braiti (pedrobraiti)
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

# Implementa o analisador léxico exigido no enunciado.
# O AFD é implementado exclusivamente com funções de estado (sem expressões
# regulares), conforme obrigatório. Cada estado do autômato é uma função
# Python que recebe um caractere e o contexto, retornando o próximo estado
# e se o cursor deve avançar.
# Estados do AFD:
#   - estado_inicial: ponto de partida, classifica o primeiro caractere
#   - estado_numero: acumula dígitos da parte inteira
#   - estado_numero_decimal: acumula dígitos após o ponto decimal
#   - estado_identificador: acumula letras maiúsculas (MEM, RES, etc.)
#   - estado_barra: diferencia '/' de '//'
# Tokens reconhecidos:
#   NUMERO           — números reais com ponto decimal (ex.: 3.14) ou inteiros
#   OPERADOR         — +, -, *, /, //, %, ^
#   PARENTESE_ABRE   — (
#   PARENTESE_FECHA  — )
#   IDENTIFICADOR    — nomes de memória em maiúsculas (MEM, VARA, TEMP, etc.)
#   KEYWORD          — palavra reservada RES (única keyword da Fase 1)
# Para visualizar melhor o AFD foi criado um diagrama de estados finitos 

from dataclasses import dataclass

class Erros(Exception):
    """Exceção para erros léxicos detectados pelo AFD."""
    pass

@dataclass
class Token:
    """Representa um token gerado pelo analisador léxico.

    Atributos:
        tipo   — classificação do token (NUMERO, OPERADOR, etc.)
        valor  — texto original extraído da entrada
        linha  — número da linha de origem (para mensagens de erro)
        coluna — posição na linha (1-indexada)
    """
    tipo: str
    valor: str
    linha: int
    coluna: int

# Constantes que definem os tipos de token reconhecidos pelo AFD
TIPO_NUMERO = "NUMERO"           # Números reais IEEE 754 64 bits (ex.: 3.14, 42)
TIPO_OPERADOR = "OPERADOR"       # Operadores: +, -, *, /, //, %, ^
TIPO_ABRE = "PARENTESE_ABRE"     # Parêntese de abertura: (
TIPO_FECHA = "PARENTESE_FECHA"   # Parêntese de fechamento: )
TIPO_IDENT = "IDENTIFICADOR"     # Nomes de memória em maiúsculas (ex.: MEM, VARA)
TIPO_KEYWORD = "KEYWORD"         # Palavra reservada: RES

# Funções auxiliares de classificação de caracteres
# Substituem regex — implementadas manualmente conforme exigido

def _eh_digito(char: str) -> bool:
    """Verifica se o caractere é um dígito [0-9] sem usar regex."""
    return "0" <= char <= "9"

def _eh_maiuscula(char: str) -> bool:
    """Verifica se o caractere é letra maiúscula [A-Z] sem usar regex."""
    return "A" <= char <= "Z"

def _eh_minuscula(char: str) -> bool:
    """Verifica se o caractere é letra minúscula [a-z] sem usar regex."""
    return "a" <= char <= "z"

def _adicionar_token(contexto: dict, tipo: str, valor: str) -> None:
    """Cria um Token e adiciona à lista de tokens no contexto do AFD."""
    contexto["tokens"].append(
        Token(tipo=tipo, valor=valor, linha=contexto["linha"], coluna=contexto["inicio_token"] + 1)
    )


# Funções de estado do AFD (cada estado é uma função)
# Cada função recebe o caractere atual e o dicionário de contexto.
# Retorna uma tupla (próximo_estado, avançar_cursor).
# Quando avançar_cursor=False, o caractere é reprocessado no próximo estado.


def estado_inicial(char: str, contexto: dict) -> tuple[str, bool]:
    """Estado inicial do AFD — classifica o primeiro caractere de cada token.

    Transições:
        espaço/tab/newline → permanece em 'inicial' (ignora whitespace)
        '('  → emite PARENTESE_ABRE, incrementa contador de parênteses
        ')'  → emite PARENTESE_FECHA, decrementa contador (erro se <= 0)
        dígito [0-9] → transita para 'numero'
        maiúscula [A-Z] → transita para 'identificador'
        +, -, *, %, ^ → emite OPERADOR
        '/' → transita para 'barra' (pode ser '/' ou '//')
        '.' → erro (ponto sem dígito antes)
        minúscula [a-z] → erro (identificadores devem ser maiúsculos)
        outro → erro (caractere inválido)
    """
    # Whitespace: ignorado pelo AFD
    if char in (" ", "\t", "\r", "\n"):
        return "inicial", True

    # Parêntese de abertura — formato RPN: (A B op)
    if char == "(":
        contexto["inicio_token"] = contexto["i"]
        _adicionar_token(contexto, TIPO_ABRE, "(")
        contexto["paren"] += 1  # Contador para detectar desbalanceamento
        return "inicial", True

    # Parêntese de fechamento — valida balanceamento
    if char == ")":
        contexto["inicio_token"] = contexto["i"]
        if contexto["paren"] <= 0:
            raise Erros(f"Linha {contexto['linha']}: ')' sem '(' correspondente")
        contexto["paren"] -= 1
        _adicionar_token(contexto, TIPO_FECHA, ")")
        return "inicial", True

    # Dígito — inicia acumulação de número (inteiro ou real)
    if _eh_digito(char):
        contexto["buffer"] = char
        contexto["inicio_token"] = contexto["i"]
        return "numero", True

    # Letra maiúscula — inicia identificador (nomes de memória ou keyword RES)
    if _eh_maiuscula(char):
        contexto["buffer"] = char
        contexto["inicio_token"] = contexto["i"]
        return "identificador", True

    # Operadores de um caractere: +, -, *, %, ^
    if char in "+-*%^":
        contexto["inicio_token"] = contexto["i"]
        _adicionar_token(contexto, TIPO_OPERADOR, char)
        return "inicial", True

    # Barra — pode ser divisão real '/' ou divisão inteira '//'
    if char == "/":
        contexto["buffer"] = "/"
        contexto["inicio_token"] = contexto["i"]
        return "barra", True

    # Erro: ponto sem dígito antes (ex.: .5)
    if char == ".":
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: número malformado — ponto sem dígito antes"
        )

    # Erro: letras minúsculas não são permitidas em identificadores
    if _eh_minuscula(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: identificadores devem usar apenas letras maiúsculas, encontrado '{char}'"
        )

    # Erro: caractere não reconhecido pela linguagem (ex.: @, $, !, &)
    raise Erros(f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: caractere inválido '{char}'")


def estado_numero(char: str, contexto: dict) -> tuple[str, bool]:
    """Estado 'numero' — acumula dígitos da parte inteira de um número.

    Transições:
        dígito → permanece em 'numero' (acumula)
        '.'    → transita para 'numero_decimal'
        letra  → erro (número malformado, ex.: 10x)
        outro  → emite NUMERO e retorna a 'inicial' sem avançar
    """
    # Continua acumulando dígitos da parte inteira
    if _eh_digito(char):
        contexto["buffer"] += char
        return "numero", True

    # Ponto decimal — transita para acumular a parte fracionária
    if char == ".":
        contexto["buffer"] += char
        return "numero_decimal", True

    # Erro: letra colada ao número (ex.: 3abc, 10x)
    if _eh_maiuscula(char) or _eh_minuscula(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"número malformado '{contexto['buffer'] + char}' — letra imediatamente após número"
        )

    # Outro caractere (espaço, parêntese, operador): emite o token NUMERO
    # e retorna ao estado inicial SEM avançar (reprocessa o caractere)
    _adicionar_token(contexto, TIPO_NUMERO, contexto["buffer"])
    contexto["buffer"] = ""
    return "inicial", False


def estado_numero_decimal(char: str, contexto: dict) -> tuple[str, bool]:
    """Estado 'numero_decimal' — acumula dígitos após o ponto decimal.

    Números reais usam ponto como separador (ex.: 3.14).
    O enunciado exige ponto (não vírgula) como separador decimal.

    Transições:
        dígito → permanece em 'numero_decimal'
        '.'    → erro (múltiplos pontos, ex.: 3.14.5)
        letra  → erro (número malformado, ex.: 2.0a)
        outro  → emite NUMERO se válido, retorna a 'inicial' sem avançar
    """
    # Continua acumulando dígitos da parte fracionária
    if _eh_digito(char):
        contexto["buffer"] += char
        return "numero_decimal", True

    # Erro: segundo ponto decimal (ex.: 3.14.5)
    if char == ".":
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"número malformado '{contexto['buffer'] + char}' — múltiplos pontos decimais"
        )

    # Erro: ponto sem dígitos depois (ex.: 3.)
    if contexto["buffer"].endswith("."):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i']}: "
            f"número malformado '{contexto['buffer']}' — ponto decimal sem dígitos depois"
        )

    # Erro: letra colada ao número decimal (ex.: 2.0a)
    if _eh_maiuscula(char) or _eh_minuscula(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"número malformado '{contexto['buffer'] + char}' — letra imediatamente após número"
        )

    # Número decimal completo — emite token e retorna sem avançar
    _adicionar_token(contexto, TIPO_NUMERO, contexto["buffer"])
    contexto["buffer"] = ""
    return "inicial", False


def estado_identificador(char: str, contexto: dict) -> tuple[str, bool]:
    """Estado 'identificador' — acumula letras maiúsculas para nomes de memória.

    Reconhece identificadores (MEM, VARA, TEMP, etc.) e a keyword RES.
    MEM pode ser qualquer conjunto de letras maiúsculas.
    RES é a única keyword da linguagem na Fase 1.

    Transições:
        maiúscula → permanece em 'identificador'
        minúscula → erro (identificadores só aceitam maiúsculas)
        dígito    → erro (identificadores só aceitam letras)
        outro     → emite KEYWORD (se RES) ou IDENTIFICADOR, sem avançar
    """
    # Continua acumulando letras maiúsculas
    if _eh_maiuscula(char):
        contexto["buffer"] += char
        return "identificador", True

    # Erro: letra minúscula em identificador (ex.: Mem em vez de MEM)
    if _eh_minuscula(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"identificador '{contexto['buffer'] + char}' contém letra minúscula — use apenas maiúsculas"
        )

    # Erro: dígito em identificador (ex.: MEM1)
    if _eh_digito(char):
        raise Erros(
            f"Linha {contexto['linha']}, coluna {contexto['i'] + 1}: "
            f"identificador '{contexto['buffer'] + char}' contém dígito — use apenas letras maiúsculas"
        )

    # Finaliza o identificador — diferencia keyword RES de nomes de memória
    valor = contexto["buffer"]
    if valor == "RES":
        _adicionar_token(contexto, TIPO_KEYWORD, valor)  # Keyword: (N RES)
    else:
        _adicionar_token(contexto, TIPO_IDENT, valor)    # Memória: MEM, VARA, etc.

    contexto["buffer"] = ""
    return "inicial", False


def estado_barra(char: str, contexto: dict) -> tuple[str, bool]:
    """Estado 'barra' — diferencia divisão real '/' de divisão inteira '//'.

    O enunciado exige suporte a ambos os operadores:
        /  — divisão real (resultado em ponto flutuante IEEE 754)
        // — divisão inteira (trunca para inteiro)

    Transições:
        '/' → emite OPERADOR '//', retorna a 'inicial'
        outro → emite OPERADOR '/', retorna a 'inicial' sem avançar
    """
    # Segunda barra: operador de divisão inteira '//'
    if char == "/":
        _adicionar_token(contexto, TIPO_OPERADOR, "//")
        contexto["buffer"] = ""
        return "inicial", True

    # Não é segunda barra: emite divisão real '/' e reprocessa o caractere
    _adicionar_token(contexto, TIPO_OPERADOR, "/")
    contexto["buffer"] = ""
    return "inicial", False


def _finalizar(contexto: dict, estado: str) -> None:
    """Finaliza a análise léxica: emite token pendente e valida parênteses.

    Chamada após consumir todos os caracteres da linha. Se o AFD parou
    no meio de um token (ex.: número ou identificador), emite o token
    acumulado no buffer. Em seguida, verifica se todos os parênteses
    foram fechados corretamente.
    """
    # Emite token pendente conforme o estado em que o AFD parou
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

    # Valida balanceamento de parênteses (exigido pelo formato RPN)
    if contexto["paren"] != 0:
        raise Erros(f"Linha {contexto['linha']}: parênteses desbalanceados")


def tokenizar_linha(linha: str, numero_linha: int = 1) -> list[Token]:
    """Função principal do analisador léxico — tokeniza uma linha de expressão RPN.

    Implementa o motor do AFD usando um dicionário que mapeia nomes de estado
    para suas funções correspondentes. Percorre cada caractere
    da entrada, delegando ao estado atual a decisão de transição.

    Args:
        linha        — string com a expressão RPN (ex.: '(3.14 2.0 +)')
        numero_linha — número da linha para mensagens de erro

    Returns:
        Lista de objetos Token extraídos da linha.

    Raises:
        Erros — se a entrada contém tokens inválidos ou parênteses desbalanceados.
    """
    # Contexto compartilhado entre todas as funções de estado do AFD
    contexto = {
        "tokens": [],          # Lista de tokens gerados
        "buffer": "",          # Buffer para acumular caracteres do token atual
        "i": 0,                # Índice do caractere sendo processado
        "inicio_token": 0,     # Posição onde o token atual começou
        "linha": numero_linha,  # Número da linha (para mensagens de erro)
        "paren": 0,            # Contador de parênteses abertos
    }

    # Estado inicial do AFD
    estado = "inicial"

    # Dicionário que mapeia nome do estado → função (motor do AFD)
    # Cada estado é uma função, conforme exigido
    maquina = {
        "inicial": estado_inicial,
        "numero": estado_numero,
        "numero_decimal": estado_numero_decimal,
        "identificador": estado_identificador,
        "barra": estado_barra,
    }

    # Adiciona '\n' ao final para forçar emissão do último token
    chars = linha + "\n"
    # Loop principal do AFD: consome caractere a caractere
    while contexto["i"] < len(chars):
        char = chars[contexto["i"]]
        # Delega ao estado atual, que retorna (próximo_estado, avancar_cursor)
        proximo_estado, avancar = maquina[estado](char, contexto)
        estado = proximo_estado
        if avancar:
            contexto["i"] += 1

    # Finaliza: emite token pendente no buffer e valida parênteses
    _finalizar(contexto, estado)
    return contexto["tokens"]
