# Analisador Léxico - Compiladores

Analisador léxico implementado como uma máquina de estados finitos (FSM) em Python.

> **Status:** Em desenvolvimento

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

O projeto implementa um **analisador léxico** (lexer) baseado em máquina de estados finitos. O lexer recebe uma linha de entrada e a decompõe em tokens, reconhecendo os seguintes tipos:

| Token | Descrição | Exemplos |
|-------|-----------|----------|
| `NUMERO` | Números inteiros e decimais | `42`, `3.14` |
| `OPERADOR` | Operadores aritméticos | `+`, `-`, `*`, `/`, `//`, `%`, `^` |
| `PARENTESE_ABRE` | Parêntese de abertura | `(` |
| `PARENTESE_FECHA` | Parêntese de fechamento | `)` |
| `IDENTIFICADOR` | Sequências de letras maiúsculas | `ABC`, `X` |
| `KEYWORD` | Palavra reservada | `RES` |

## Estrutura

```
Analisador_Lexico-Compiladores/
├── README.md
└── src/
    └── lexer_fsm.py
```

## Como usar

```python
from src.lexer_fsm import tokenizar_linha

tokens = tokenizar_linha("3 + 42 * (X - 1)")
for t in tokens:
    print(f"{t.tipo}: {t.valor}")
```

## Estados da FSM

- **inicial** — Estado de partida; identifica o tipo do próximo token.
- **numero** — Lendo dígitos de um número inteiro.
- **numero_decimal** — Lendo parte decimal de um número.
- **identificador** — Lendo letras maiúsculas.
- **barra** — Lido `/`; decide entre divisão (`/`) e divisão inteira (`//`).