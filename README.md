# Analisador Léxico - Compiladores

Analisador léxico implementado como uma máquina de estados finitos (FSM) em Python.

## Integrantes

| Nome |
|------|
| Arthur Felipe Bach Biancolini |
| Emanuel Riceto da Silva |
| Frederico Virmond Fruet |
| Pedro Alessandrini Braiti |

- **Grupo Canvas:** RA1 18
- **Instituição:** Pontifícia Universidade Católica do Paraná
- **Disciplina:** Linguagens Formais e Compiladores
- **Professor:** Frank Coelho de Alcantara

## Descrição

O projeto implementa um **analisador léxico** (lexer) baseado em máquina de estados finitos (AFD). O lexer recebe uma expressão em notação pré-fixada (polonesa) e a decompõe em tokens, validando a estrutura léxica da entrada.

A análise léxica é a **primeira fase de um compilador**: ela lê o código-fonte caractere a caractere e agrupa esses caracteres em unidades significativas chamadas **tokens** (por exemplo, um número `3.14`, um operador `+` ou um identificador `MEM`). Erros nessa fase — como caracteres ilegais ou números malformados — são detectados antes de qualquer processamento sintático ou semântico.

## Funcionamento do código

### Arquitetura geral

O lexer é organizado como uma **máquina de estados explícita** dentro da função `tokenizar_linha()`. A ideia central é:

1. Um dicionário `maquina` mapeia o nome de cada estado para a sua função correspondente.
2. Um dicionário `contexto` carrega todo o estado mutável da análise: lista de tokens produzidos, buffer de caracteres em acumulação, posição atual (`i`), número da linha e contador de parênteses abertos (`paren`).
3. Um laço `while` percorre a string de entrada caractere a caractere, chamando a função do estado atual e recebendo de volta o **próximo estado** e um booleano indicando se o ponteiro deve avançar.

```
entrada: "(3.14 2.0 +)"
         ↑
         i=0  estado=inicial
```

O truque de retornar `avancar=False` permite que um estado "devolva" o caractere atual para o próximo estado reprocessá-lo — por exemplo, quando o estado `numero` encontra um espaço, ele emite o token numérico e retorna ao estado `inicial` **sem consumir** o espaço, que será tratado pelo próprio `inicial`.

### Contexto (`contexto: Dict`)

| Chave | Tipo | Finalidade |
|-------|------|-----------|
| `tokens` | `List[Token]` | Lista de tokens já emitidos. |
| `buffer` | `str` | Caracteres acumulados do token em construção (ex: `"3.1"` enquanto lê `3.14`). |
| `i` | `int` | Índice do caractere atual na string de entrada. |
| `inicio_token` | `int` | Posição do primeiro caractere do token sendo construído (usada para gravar a coluna). |
| `linha` | `int` | Número da linha (recebido como parâmetro, para suportar entrada multilinha). |
| `paren` | `int` | Contador de parênteses: incrementa em `(`, decrementa em `)`. Deve ser zero ao final. |

### Fluxo estado a estado

**`estado_inicial`** — Ponto de entrada para cada novo token. Classifica o caractere atual:
- Espaço/tab/newline → ignora (permanece em `inicial`).
- `(` → emite `PARENTESE_ABRE`, incrementa `paren`.
- `)` → verifica se há `(` aberto, emite `PARENTESE_FECHA`, decrementa `paren`.
- Dígito `[0-9]` → inicia buffer, transita para `numero`.
- Letra maiúscula `[A-Z]` → inicia buffer, transita para `identificador`.
- Operador `+-*%^` → emite `OPERADOR` imediatamente (token de um caractere).
- `/` → transita para `barra` (precisa olhar o próximo caractere para decidir entre `/` e `//`).
- `.` sem dígito antes, letra minúscula, ou qualquer outro caractere → lança `Erros`.

**`estado_numero`** — Acumula dígitos no buffer:
- Dígito → concatena ao buffer, permanece em `numero`.
- `.` → concatena ao buffer, transita para `numero_decimal`.
- Letra → erro (número malformado como `42abc`).
- Qualquer outro caractere → emite o token `NUMERO` com o conteúdo do buffer e retorna a `inicial` **sem consumir** o caractere (para ser reprocessado).

**`estado_numero_decimal`** — Acumula a parte fracionária:
- Dígito → concatena, permanece.
- Segundo `.` → erro (múltiplos pontos).
- Buffer termina em `.` (nenhum dígito após o ponto) → erro.
- Letra → erro.
- Outro → emite `NUMERO` e retorna a `inicial` sem consumir.

**`estado_identificador`** — Acumula letras maiúsculas:
- Maiúscula → concatena, permanece.
- Minúscula → erro (identificador com `Mem` em vez de `MEM`).
- Dígito → erro (identificador com `MEM1`).
- Outro → verifica se o valor acumulado é `"RES"` (emite `KEYWORD`) ou não (emite `IDENTIFICADOR`), retorna a `inicial` sem consumir.

**`estado_barra`** — Resolve ambiguidade de `/` vs `//`:
- Segundo `/` → emite `OPERADOR` com valor `"//"`.
- Outro → emite `OPERADOR` com valor `"/"` e retorna a `inicial` sem consumir.

**`_finalizar`** — Chamada após o laço terminar:
- Se o autômato parou em `numero`, `numero_decimal`, `identificador` ou `barra`, emite o token pendente no buffer.
- Verifica se `paren == 0`; caso contrário, lança erro de parênteses desbalanceados.

### Classe `Token`

Cada token é um `dataclass` com quatro campos:

```python
@dataclass
class Token:
    tipo: str      # ex: "NUMERO", "OPERADOR"
    valor: str     # ex: "3.14", "+"
    linha: int     # número da linha na entrada
    coluna: int    # posição (1-indexada) do primeiro caractere do token
```

### Classe `Erros`

Exceção customizada que herda de `Exception`. É lançada sempre que o lexer encontra uma situação inválida, carregando uma mensagem com **linha**, **coluna** e **descrição** do problema.

### Tokens reconhecidos

| Token | Descrição | Exemplos |
|-------|-----------|----------|
| `NUMERO` | Números inteiros e decimais | `42`, `3.14`, `123456.789` |
| `OPERADOR` | Operadores aritméticos | `+`, `-`, `*`, `/`, `//`, `%`, `^` |
| `PARENTESE_ABRE` | Parêntese de abertura | `(` |
| `PARENTESE_FECHA` | Parêntese de fechamento | `)` |
| `IDENTIFICADOR` | Nomes de variáveis (apenas letras maiúsculas) | `MEM`, `CONTADOR`, `VARA` |
| `KEYWORD` | Palavra reservada | `RES` |

### Tratamento de erros

O lexer detecta e reporta com mensagens descritivas os seguintes erros:

| Erro | Exemplo | Mensagem |
|------|---------|----------|
| Caractere inválido | `(3 2 @)` | caractere inválido |
| Letra minúscula como identificador | `(3.0 abc +)` | identificadores devem usar apenas letras maiúsculas |
| Número seguido de letra | `(3.14abc 2 +)` | número malformado — letra imediatamente após número |
| Múltiplos pontos decimais | `(3.14.5 2 +)` | múltiplos pontos decimais |
| Ponto sem dígito antes | `(.5 2 +)` | ponto sem dígito antes |
| Ponto sem dígito depois | `(3. 2 +)` | ponto decimal sem dígitos depois |
| Identificador com dígito | `(10.5 MEM1)` | identificador contém dígito |
| Identificador com minúscula | `(10.5 Mem)` | identificador contém letra minúscula |
| Parênteses desbalanceados | `((3 2 +)` | parênteses desbalanceados |
| `)` sem `(` correspondente | `3 2 +)` | ')' sem '(' correspondente |

## Diagrama da FSM

![AFD do Analisador Léxico](docs/afd_lexer.png)

### Estados

| Estado | Descrição |
|--------|-----------|
| **INICIAL** | Estado de partida; identifica o tipo do próximo token pelo caractere lido. |
| **NUMERO** | Acumulando dígitos de um número inteiro. Transita para NUMERO_DECIMAL ao encontrar `.`. |
| **NUMERO_DECIMAL** | Acumulando dígitos da parte fracionária. |
| **IDENTIFICADOR** | Acumulando letras maiúsculas. Ao finalizar, emite `KEYWORD` se for `RES`, senão `IDENTIFICADOR`. |
| **BARRA** | Lido `/`; decide entre divisão (`/`) e divisão inteira (`//`). |
| **FINALIZAR** | Emite token pendente no buffer e verifica balanceamento de parênteses. |
| **ERRO_LEXICO** | Estado de erro — lança exceção `Erros` com mensagem descritiva. |

## Estrutura do projeto

```
Analisador_Lexico-Compiladores/
├── README.md
├── src/
│   └── lexer_fsm.py       # Implementação do analisador léxico (FSM)
└── tests/
    └── test_lexer.py       # Testes unitários (30 casos)
```

## Como usar

```python
from src.lexer_fsm import tokenizar_linha

tokens = tokenizar_linha("(3.14 2.0 +)")
for t in tokens:
    print(f"{t.tipo:<16} {t.valor}")
```

Saída:

```
PARENTESE_ABRE   (
NUMERO           3.14
NUMERO           2.0
OPERADOR         +
PARENTESE_FECHA  )
```

## Como executar os testes

```bash
python -m unittest tests/test_lexer.py -v
```

Os testes cobrem:
- **Entradas válidas:** expressões simples, aninhadas, todos os operadores, identificadores e keyword `RES`.
- **Entradas inválidas:** 17 cenários de erro, verificando tanto a exceção quanto o conteúdo da mensagem.