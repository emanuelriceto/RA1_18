# RA1 18 Linguagens Formais e Compiladores

| | |
|---|---|
| **Instituição** | Pontifícia Universidade Católica do Paraná |
| **Disciplina** | Linguagens Formais e Compiladores |
| **Professor** | Frank Coelho de Alcantara |
| **Grupo Canvas** | RA1 18 |

### Integrantes 

| Nome |
|---|
| Arthur Felipe Bach Biancolini (Tuizones) |
| Emanuel Riceto da Silva (emanuelriceto) |
| Frederico Virmond Fruet (fredfruet) |
| Pedro Alessandrini Braiti (pedrobraiti) |

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

### Números Negativos

Em Notação Polonesa Reversa não existe ambiguidade entre o operador de subtração e a negação unária, como ocorre na notação infixa. O caractere `-` é **sempre** um operador binário que recebe dois operandos. Para representar um número negativo, basta subtrair o valor de zero:

| Valor desejado | Expressão RPN | Resultado |
|---|---|---|
| −3 | `(0 3 -)` | 0 − 3 = −3 |
| −7.5 | `(0 7.5 -)` | 0 − 7.5 = −7.5 |
| −1 × (4 + 2) | `(0 (4 2 +) -)` | 0 − 6 = −6 |

Essa abordagem elimina a necessidade de um operador unário de negação e mantém a gramática da linguagem simples e uniforme — todos os operadores (`+`, `-`, `*`, `/`, `//`, `%`, `^`) são estritamente binários.

---

## Fluxo de Execução (Pipeline)

O programa segue um pipeline sequencial de 5 etapas, desde a leitura do arquivo até a geração final do Assembly:

```
 Arquivo .txt ──► lerArquivo() ──► parseExpressao() ──► executarExpressao() ──► gerarAssembly() ──► exibirResultados()
     │                │                  │                     │                     │                    │
  entrada        lista de           tokens (AFD)          validação            código .s           console
  de texto        linhas            + árvore AST          semântica          ARMv7 completo
```

### Etapa 1 — Leitura (`lerArquivo`)

Recebe o caminho do arquivo e uma lista vazia. Lê linha a linha, descartando:
- Linhas em branco
- Linhas que começam com `#` (comentários)

As linhas restantes são adicionadas à lista para processamento.

### Etapa 2 — Análise Léxica e Parsing (`parseExpressao`)

Cada linha passa pela função `tokenizar_linha()` do AFD (`lexer_fsm.py`), que produz uma lista de objetos `Token`, cada um com:
- `tipo` — classificação do token (`NUMERO`, `OPERADOR`, `PARENTESE_ABRE`, `PARENTESE_FECHA`, `IDENTIFICADOR`, `KEYWORD`)
- `valor` — texto original do token
- `linha` e `coluna` — posição no arquivo de entrada

Em seguida, os tokens são organizados em uma **Árvore Sintática Abstrata (AST)** por um parser recursivo descendente. Os tipos de nós da AST são:

| Nó da AST | Exemplo de entrada | Descrição |
|---|---|---|
| `binary` | `(3.0 2.0 +)` | Operação binária com operandos esquerdo, direito e operador |
| `number` | `3.14` | Literal numérico (inteiro ou decimal) |
| `ident` | `MEM` | Identificador em letras maiúsculas |
| `mem_write` | `(10.5 VARA)` | Escrita de valor em variável de memória |
| `mem_read` | `(VARA)` | Leitura de variável de memória |
| `res_ref` | `(2 RES)` | Referência ao resultado de N linhas anteriores |

Expressões aninhadas como `((3.0 2.0 +) (4.0 1.0 -) *)` geram ASTs com sub-árvores recursivas.

### Etapa 3 — Validação Semântica (`executarExpressao`)

Processa a AST e valida a semântica da expressão:
- **`mem_write`**: registra a variável como definida no dicionário `contexto["memoria"]`.
- **`mem_read`**: verifica se a variável existe; se não, marca como `"não inicializada"`.
- **`res_ref`**: valida se o índice `N` é alcançável — por exemplo, `(2 RES)` na primeira linha gera erro porque não existem 2 resultados anteriores.
- **`binary`**: aceita a expressão como válida (o cálculo real é delegado ao Assembly).

O contexto é compartilhado entre todas as linhas, permitindo que uma expressão referencie memórias ou resultados definidos por expressões anteriores.

### Etapa 4 — Geração de Assembly (`gerarAssembly`)

Percorre as ASTs de todas as linhas e gera código Assembly ARMv7 completo. O gerador utiliza uma **avaliação baseada em pilha (stack-based)**: cada operando é carregado em `d0` e empilhado via `PUSH`; operações binárias desempilham dois operandos, operam e reempilham o resultado.

O código gerado inclui:
- **Seção `.text`** — instruções executáveis com prefixo `_start:`
- **Seção `.data`** — constantes `.double`, variáveis de memória (`mem_*`), resultados por linha (`resultado_N`)
- **Rotinas auxiliares** — `__op_idiv`, `__op_mod`, `__op_pow`, `__sdiv32`, `__exibir_hex`, `__udiv_simples`

### Etapa 5 — Exibição (`exibirResultados`)

Imprime no console uma descrição de cada linha processada, no formato:

```
Linha 1: expressão válida
Linha 2: memória VARA marcada como definida
Linha 3: leitura da memória VARA
Linha 4: referência ao resultado de 1 linhas atrás
```

---

## Exemplo de Uso

### Arquivo de entrada (`teste1.txt`)

```
(3.0 2.0 +)
(10.0 4.0 -)
(2.5 8.0 *)
(9.0 3.0 /)
(10 3 //)
(10 3 %)
(2 5 ^)
((3.0 2.0 +) (4.0 1.0 -) *)
(2 RES)
(12.5 MEM)
(MEM)
```

### Tokens gerados (`tokens_ultima_execucao.txt`)

```
linha_1;PARENTESE_ABRE:(,NUMERO:3.0,NUMERO:2.0,OPERADOR:+,PARENTESE_FECHA:)
linha_2;PARENTESE_ABRE:(,NUMERO:10.0,NUMERO:4.0,OPERADOR:-,PARENTESE_FECHA:)
...
```

### Assembly gerado (trecho simplificado)

```asm
.syntax unified
.cpu cortex-a9
.fpu vfpv3
.global _start

.text
_start:
    @ Expressão 1
    LDR r0, =const_0          @ carrega 3.0
    VLDR.F64 d0, [r0]
    VMOV r4, r5, d0
    PUSH {r4, r5}
    LDR r0, =const_1          @ carrega 2.0
    VLDR.F64 d0, [r0]
    VMOV r4, r5, d0
    PUSH {r4, r5}
    POP {r4, r5}               @ desempilha 2.0 → d1
    VMOV d1, r4, r5
    POP {r4, r5}               @ desempilha 3.0 → d0
    VMOV d0, r4, r5
    VADD.F64 d0, d0, d1       @ d0 = 3.0 + 2.0 = 5.0
    ...
    BL __exibir_hex            @ mostra 5 no display HEX

.data
const_0: .double 3.0
const_1: .double 2.0
resultado_0: .double 0.0
```

---

## Estrutura do Projeto

```
.
├── main.py                          # Ponto de entrada (CLI)
├── README.md
├── teste1.txt                   # 11 expressões — operadores básicos
├── teste2.txt                   # 10 expressões — variável VARA
├── teste3.txt                   # 10 expressões — variável TEMP
├── src/
│   ├── lexer_fsm.py                 # AFD — analisador léxico
│   ├── pipeline.py                  # Funções obrigatórias do enunciado
│   └── armv7_generator.py           # Gerador de Assembly ARMv7
│
├── tests/
│   ├── test_lexer.py                # 26 testes do analisador léxico
│   └── test_pipeline.py             # 12 testes do pipeline e geração
│
│
├── output/
    ├── ultima_execucao.s            # Assembly gerado na última execução
    └── tokens_ultima_execucao.txt   # Tokens da última execução

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
python main.py teste1.txt
```

Os arquivos de saída são gerados automaticamente em `output/`:
- `output/ultima_execucao.s` — código Assembly ARMv7
- `output/tokens_ultima_execucao.txt` — tokens no formato `TIPO:valor`

Caminhos personalizados:

```bash
python main.py teste2.txt --out output/teste2.s --tokens-out output/tokens_teste2.txt
```

### Testes automatizados

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Resultado esperado: **38 testes** (26 léxicos + 12 pipeline), todos passando.

#### Testes do Lexer (`test_lexer.py` — 26 testes)

| Categoria | Testes | O que valida |
|---|---|---|
| Entradas válidas | 7 | Expressões simples, todos os 7 operadores, expressões aninhadas (dupla e tripla) |
| Tipos de token | 6 | Tipo correto de cada token (`NUMERO`, `OPERADOR`, `ABRE`, `FECHA`, `IDENT`, `KEYWORD`) |
| Memória e RES | 3 | Leitura/escrita de memória, keyword `RES` |
| Números | 2 | Inteiros, decimais grandes (`123456.789`) |
| Erros léxicos | 8 | Operador inválido (`&`, `!`, `@`, `$`), número malformado (`3.14.5`, `3.`), vírgula decimal, minúsculas, identificador com dígito |
| Erros estruturais | 4 | Parênteses desbalanceados, `)` extra, `(` faltando |

#### Testes do Pipeline (`test_pipeline.py` — 12 testes)

| Categoria | Testes | O que valida |
|---|---|---|
| Fluxo completo | 1 | Todas as operações de uma vez — verifica presença das rotinas auxiliares e rótulos no Assembly |
| Geração Assembly | 3 | Instruções corretas para cada operador (`VADD`, `VSUB`, `VMUL`, `VDIV`, `BL __op_*`), expressões aninhadas, IEEE 754 64 bits (`.double`, `F64`) |
| `parseExpressao` | 1 | Lista de strings dos tokens retornada corretamente |
| `executarExpressao` | 4 | Expressão simples, escrita em memória, leitura de memória, referência RES válida |
| Erro semântico | 1 | `(1 RES)` sem resultados anteriores lança `Erros` |
| `lerArquivo` | 1 | Ignora comentários (`#`) e linhas em branco |

### Carregar no CPUlator

1. Abrir [cpulator.01xz.net](https://cpulator.01xz.net/?sys=arm-de1soc&d_audio=48000) com **ARMv7 — DE1-SoC**.
2. Colar o conteúdo de `output/ultima_execucao.s` no editor.
3. Compilar e executar (`F5`).
4. Observar o resultado no display **HEX3–HEX0** (valor inteiro truncado do resultado da última expressão com `RES`).

---

## Autômato Finito Determinístico (AFD)

O analisador léxico (`lexer_fsm.py`) é implementado como um AFD com as seguintes características:

- **5 estados**: `estado_inicial`, `estado_numero`, `estado_numero_decimal`, `estado_identificador`, `estado_barra`
- **Sem expressões regulares** — cada estado é uma função Python pura que recebe um caractere e o contexto, retornando o próximo estado e se deve avançar o cursor
- **Motor por dicionário**: mapeia nome do estado → função, consumindo caractere a caractere com mecanismo de avanço/não-avanço

### Tabela de Transições

| Estado atual | Entrada | Próximo estado | Ação |
|---|---|---|---|
| `inicial` | espaço / tab / `\n` | `inicial` | Ignora whitespace |
| `inicial` | `(` | `inicial` | Emite `PARENTESE_ABRE`, incrementa contador de parênteses |
| `inicial` | `)` | `inicial` | Emite `PARENTESE_FECHA`, decrementa contador (erro se ≤ 0) |
| `inicial` | dígito `[0-9]` | `numero` | Inicia buffer numérico |
| `inicial` | maiúscula `[A-Z]` | `identificador` | Inicia buffer de identificador |
| `inicial` | `+ - * % ^` | `inicial` | Emite `OPERADOR` |
| `inicial` | `/` | `barra` | Aguarda possível `//` |
| `inicial` | `.` | **ERRO** | Ponto sem dígito antes |
| `inicial` | minúscula `[a-z]` | **ERRO** | Identificadores devem ser maiúsculos |
| `numero` | dígito | `numero` | Acumula no buffer |
| `numero` | `.` | `numero_decimal` | Transição para parte decimal |
| `numero` | letra | **ERRO** | Número malformado (letra após número) |
| `numero` | outro | `inicial` | Emite `NUMERO`, **não avança** (reprocessa caractere) |
| `numero_decimal` | dígito | `numero_decimal` | Acumula no buffer |
| `numero_decimal` | `.` | **ERRO** | Múltiplos pontos decimais |
| `numero_decimal` | letra | **ERRO** | Número malformado |
| `numero_decimal` | outro | `inicial` | Emite `NUMERO` (valida que não termina em `.`) |
| `identificador` | maiúscula | `identificador` | Acumula no buffer |
| `identificador` | minúscula | **ERRO** | Letra minúscula em identificador |
| `identificador` | dígito | **ERRO** | Dígito em identificador |
| `identificador` | outro | `inicial` | Emite `KEYWORD` (se `RES`) ou `IDENTIFICADOR`, **não avança** |
| `barra` | `/` | `inicial` | Emite `OPERADOR` com valor `//` |
| `barra` | outro | `inicial` | Emite `OPERADOR` com valor `/`, **não avança** |

### Estado de Finalização

Ao consumir todos os caracteres, a função `_finalizar()`:
1. Emite qualquer token pendente no buffer (número, identificador ou `/`)
2. Verifica se o contador de parênteses é zero — caso contrário, lança `Erros("parênteses desbalanceados")`

### Tratamento de Erros Léxicos

O AFD detecta e reporta com posição exata (linha e coluna):

| Erro | Exemplo | Mensagem |
|---|---|---|
| Caractere inválido | `(3 2 @)` | `caractere inválido '@'` |
| Letra minúscula | `(3.0 abc +)` | `identificadores devem usar apenas letras maiúsculas` |
| Número malformado | `(3.14.5 2 +)` | `múltiplos pontos decimais` |
| Ponto sem dígito | `(.5 2 +)` | `ponto sem dígito antes` |
| Número + letra | `(10x 2 +)` | `letra imediatamente após número` |
| Identificador + dígito | `(10.5 MEM1)` | `identificador contém dígito` |
| Identificador misto | `(10.5 Mem)` | `contém letra minúscula` |
| `)` sem `(` | `3 2 +)` | `')' sem '(' correspondente` |
| `(` sem `)` | `(3 2 +` | `parênteses desbalanceados` |

---

## Detalhes Técnicos

### Assembly ARMv7

O gerador (`armv7_generator.py`) percorre recursivamente cada AST e emite instruções ARMv7 usando uma **estratégia de avaliação baseada em pilha**:

1. **Operandos** (números, leitura de memória, referência RES): carregados em `d0` via `VLDR.F64`, depois empilhados com `VMOV r4, r5, d0` + `PUSH {r4, r5}`.
2. **Operações binárias**: desempilham dois operandos (`POP` → `VMOV` para `d0` e `d1`), executam a instrução e reempilham o resultado.
3. **Escrita em memória**: avalia a sub-expressão, desempilha e armazena via `VSTR.F64` no rótulo `mem_*`.
4. **Resultado final de cada linha**: desempilhado, armazenado em `resultado_N` e exibido no display HEX.

| Recurso | Implementação |
|---|---|
| Ponto flutuante | IEEE 754 64 bits (`.double`, registradores `d0`–`d7`, FPU VFPv3) |
| Soma / Subtração / Multiplicação / Divisão | Instruções nativas `VADD.F64`, `VSUB.F64`, `VMUL.F64`, `VDIV.F64` |
| Divisão inteira `//` | Rotina `__op_idiv` — converte para `S32` via `VCVT`, chama `__sdiv32` (subtração iterativa com tratamento de sinal), converte de volta para `F64` |
| Módulo `%` | Rotina `__op_mod` — converte para `S32`, calcula `A - (A/B)*B` usando `__sdiv32` + `MUL` + `SUB` |
| Potência `^` | Rotina `__op_pow` — multiplicação iterativa (`VMUL.F64` em loop) para expoente inteiro positivo; retorna `1.0` se expoente ≤ 0 |
| Divisão inteira com sinal | Rotina `__sdiv32` — normaliza sinais via `RSB`/`EOR`, loop de subtração, restaura sinal; retorna 0 em divisão por zero |
| Display HEX | Rotina `__exibir_hex` — decompõe o valor inteiro em até 4 dígitos decimais (unidades, dezenas, centenas, milhares) via divisões por 10, consulta `__hex_tabela` (7 segmentos: `0x3F`=0 … `0x6F`=9), combina com `ORR` e deslocamentos `LSL #8/16/24`, escreve em `0xFF200020`. Números negativos exibem `-` no dígito mais significativo (segmento `g` = `0x40`) |

### Gerenciamento de Dados (`.data`)

| Rótulo | Conteúdo |
|---|---|
| `const_N` | Constantes numéricas únicas (`.double`) — deduplicadas pelo gerador |
| `const_one` | Constante `1.0` usada pela rotina de potência |
| `mem_*` | Variáveis de memória, inicializadas em `0.0` |
| `resultado_N` | Resultado de cada linha (N = 0, 1, 2, …) |
| `__hex_tabela` | 10 bytes com os padrões de 7 segmentos para dígitos 0–9 |

### Formato dos Tokens

Cada linha do arquivo de tokens segue o formato:

```
linha_N;TIPO1:valor1,TIPO2:valor2,...
```

Tipos possíveis: `NUMERO`, `OPERADOR`, `PARENTESE_ABRE`, `PARENTESE_FECHA`, `IDENTIFICADOR`, `KEYWORD`.


