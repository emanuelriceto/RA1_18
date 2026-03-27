# Fase 1 — Analisador Léxico e Gerador de Assembly ARMv7 (DE1-SoC v16.1)

| | |
|---|---|
| **Instituição** | Pontifícia Universidade Católica do Paraná |
| **Disciplina** | Linguagens Formais e Compiladores |
| **Professor** | Frank Coelho de Alcantara |
| **Grupo Canvas** | RA1 18 |

### Integrantes 

| Nome |
|---|
| Arthur Felipe Bach Biancolini |
| Emanuel Riceto da Silva |
| Frederico Virmond Fruet |
| Pedro Alessandrini Braiti |

---

## Objetivo

Programa em Python que lê um arquivo de texto contendo expressões aritméticas em **Notação Polonesa Reversa (RPN)**, realiza **análise léxica** por meio de um **Autômato Finito Determinístico (AFD)** implementado exclusivamente com funções de estado (sem expressões regulares), e gera código **Assembly ARMv7** compatível com o simulador **CPUlator DE1-SoC v16.1**.

### Funcionalidades

- Leitura de arquivo `.txt` com uma expressão RPN por linha.
- Análise léxica via AFD com 5 estados (funções), sem uso de regex.
- Suporte a 7 operadores: `+`, `-`, `*`, `/`, `//`, `%`, `^`.
- Comandos especiais: `MEM` (leitura), `(valor MEM)` (escrita) e `(valor RES)` (resultado).
- Aritmética em ponto flutuante IEEE 754 de 64 bits (`.double`, instruções `VLDR`/`VSTR`/`VADD`/`VSUB`/`VMUL`/`VDIV`).
- Exibição do resultado no display HEX (HEX3–HEX0) da DE1-SoC via endereço `0xFF200020`.
- Salvamento dos tokens da última execução em arquivo texto com formato `TIPO:valor`.

---

## Estrutura do Projeto

```
.
├── main.py                          # Ponto de entrada (CLI)
├── requirements.txt                 # Dependências (stdlib apenas)
├── README.md
│
├── src/
│   ├── lexer_fsm.py                 # AFD — analisador léxico
│   ├── pipeline.py                  # Funções obrigatórias do enunciado
│   └── armv7_generator.py           # Gerador de Assembly ARMv7
│
├── tests/
│   ├── test_lexer.py                # 26 testes do analisador léxico
│   └── test_pipeline.py             # 12 testes do pipeline e geração
│
├── exemplos/
│   ├── teste1.txt                   # 11 expressões — operadores básicos
│   ├── teste2.txt                   # 10 expressões — variável VARA
│   └── teste3.txt                   # 10 expressões — variável TEMP
│
├── output/
│   ├── ultima_execucao.s            # Assembly gerado na última execução
│   └── tokens_ultima_execucao.txt   # Tokens da última execução
│
└── docs/
    └── FSM_LEXER.md                 # Documentação do AFD (diagrama + tabela)
```

---

## Funções Obrigatórias

As cinco funções exigidas pelo enunciado estão em `src/pipeline.py`:

| Função | Descrição |
|---|---|
| `lerArquivo(nomeArquivo, linhas)` | Lê o arquivo, ignora comentários (`#`) e linhas em branco |
| `parseExpressao(linha, tokens_saida)` | Tokeniza a linha via AFD e constrói a árvore sintática |
| `executarExpressao(tokens, contexto)` | Processa tokens (delega cálculos ao Assembly) |
| `gerarAssembly(tokens_por_linha, codigoAssembly)` | Gera o código Assembly ARMv7 completo |
| `exibirResultados(resultados)` | Exibe os resultados no console |

---

## Como Executar

### Execução principal

```bash
python main.py exemplos/teste1.txt
```

Os arquivos de saída são gerados automaticamente em `output/`:
- `output/ultima_execucao.s` — código Assembly ARMv7
- `output/tokens_ultima_execucao.txt` — tokens no formato `TIPO:valor`

Caminhos personalizados:

```bash
python main.py exemplos/teste2.txt --out output/teste2.s --tokens-out output/tokens_teste2.txt
```

### Testes automatizados

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Resultado esperado: **38 testes** (26 léxicos + 12 pipeline), todos passando.

### Carregar no CPUlator

1. Abrir [cpulator.01xz.net](https://cpulator.01xz.net/?sys=arm-de1soc) com **ARMv7 — DE1-SoC**.
2. Colar o conteúdo de `output/ultima_execucao.s` no editor.
3. Compilar e executar (`F5`).
4. Observar o resultado no display **HEX3–HEX0** (valor inteiro truncado do resultado da última expressão com `RES`).

---

## Autômato Finito Determinístico (AFD)

O analisador léxico é implementado como um AFD com as seguintes características:

- **5 estados**: `estado_inicial`, `estado_numero`, `estado_numero_decimal`, `estado_identificador`, `estado_barra`
- **Sem expressões regulares** — cada estado é uma função Python pura
- **Motor por dicionário**: mapeia nome do estado → função, consumindo caracteres com mecanismo de avanço/não-avanço

A documentação completa (diagrama de estados, tabela de transições, definição formal) está em [`docs/FSM_LEXER.md`](docs/FSM_LEXER.md).

---

## Detalhes Técnicos

### Assembly ARMv7

| Recurso | Implementação |
|---|---|
| Ponto flutuante | IEEE 754 64 bits (`.double`, registradores `d0`–`d7`) |
| Divisão inteira `//` | Rotina `__op_idiv` com `__sdiv32` (subtração iterativa) |
| Módulo `%` | Rotina `__op_mod` (`VCVT` → divisão inteira → subtração do produto) |
| Potência `^` | Rotina `__op_pow` (multiplicação iterativa, expoente inteiro) |
| Display HEX | Rotina `__exibir_hex` — decompõe até 4 dígitos, consulta `__hex_tabela` (7 segmentos), escreve em `0xFF200020` |

### Formato dos Tokens

Cada linha do arquivo de tokens segue o formato:

```
linha_N;TIPO1:valor1,TIPO2:valor2,...
```

Tipos possíveis: `NUMERO`, `OPERADOR`, `PARENTESE_ABRE`, `PARENTESE_FECHA`, `IDENTIFICADOR`, `KEYWORD`.

---

## Checklist de Entrega (Fase 1)

- [x] Código-fonte em Python (sem bibliotecas externas)
- [x] AFD implementado por funções de estado (sem regex)
- [x] 7 operadores suportados (`+`, `-`, `*`, `/`, `//`, `%`, `^`)
- [x] Comandos `MEM`, `(valor MEM)` e `(valor RES)`
- [x] 3 arquivos de teste com ≥ 10 linhas cada
- [x] 38 testes automatizados (léxico + pipeline)
- [x] Geração de Assembly ARMv7 para CPUlator DE1-SoC v16.1
- [x] Aritmética IEEE 754 de 64 bits
- [x] Saída no display HEX da DE1-SoC
- [x] Tokens da última execução salvos em `output/`
- [x] Identificação completa nos arquivos de código
- [x] Documentação do AFD em `docs/FSM_LEXER.md`
- [x] README com instruções de execução
