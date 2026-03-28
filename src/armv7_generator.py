# Integrantes:
#   Arthur Felipe Bach Biancolini (Tuizones)
#   Emanuel Riceto da Silva (emanuelriceto)
#   Frederico Virmond Fruet (fredfruet)
#   Pedro Alessandrini Braiti (pedrobraiti)
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

# Gera código Assembly ARMv7 funcional a partir da AST das expressões RPN.
# O Assembly gerado é compatível com o simulador CPUlator 
#
# Avaliação baseada em pilha (stack-based): operandos são empilhados
# e operações desempilham dois valores, operam e reempilham.
# Aritmética em ponto flutuante IEEE 754 de 64 bits (.double, FPU VFPv3)
# Saída no display HEX (HEX3–HEX0) via endereço 0xFF200020




def _normalizar_nome_mem(nome: str) -> str:
    """Normaliza nome de memória para minúsculas (rótulos no Assembly)."""
    return nome.lower()


def _coletar_memorias(no: dict, memorias: set[str]) -> None:
    """Percorre a AST recursivamente coletando nomes de variáveis de memória.

    Necessário para pré-declarar todas as variáveis na seção .data
    do Assembly antes da execução (mem_vara: .double 0.0, etc.).
    """
    tipo = no["tipo"]
    if tipo == "mem_write":
        memorias.add(_normalizar_nome_mem(no["nome"]))
        _coletar_memorias(no["valor"], memorias)
    elif tipo == "mem_read":
        memorias.add(_normalizar_nome_mem(no["nome"]))
    elif tipo == "binary":
        _coletar_memorias(no["esq"], memorias)
        _coletar_memorias(no["dir"], memorias)



# Funções de emissão de instruções Assembly (pilha de operandos)
# A estratégia usa a pilha do processador para armazenar valores F64:
#   VMOV r4, r5, d0 + PUSH {r4, r5}   → empilha d0 (8 bytes = 64 bits)
#   POP {r4, r5} + VMOV dN, r4, r5     → desempilha para registrador dN


def _emit_push_d0(linhas: list[str]) -> None:
    """Emite instruções para empilhar d0 (IEEE 754 64 bits) na pilha ARM."""
    linhas.append("    VMOV r4, r5, d0")
    linhas.append("    PUSH {r4, r5}")


def _emit_pop_para_d(linhas: list[str], reg_d: str) -> None:
    """Emite instruções para desempilhar da pilha ARM para registrador FP."""
    linhas.append("    POP {r4, r5}")
    linhas.append(f"    VMOV {reg_d}, r4, r5")



# Emissão recursiva de instruções para cada nó da AST
# Percorre a árvore em profundidade, gerando Assembly para cada nó.
# Expressões aninhadas são tratadas naturalmente pela recursão.


def _emit_expressao(
    no: dict,
    linhas: list[str],
    mapa_constantes: dict[str, str],
    contador_constantes: list[int],
    indice_linha: int,
) -> None:
    """Gera instruções Assembly para um nó da AST, recursivamente.

    Cada tipo de nó gera instruções específicas:
        number    — carrega constante .double via LDR + VLDR.F64
        mem_read  — carrega variável de memória via VLDR.F64
        res_ref   — carrega resultado anterior via VLDR.F64
        mem_write — avalia valor e armazena via VSTR.F64
        binary    — avalia operandos, desempilha e aplica operação
    """
    tipo = no["tipo"]

    # Número literal — carrega constante IEEE 754 64 bits (.double)
    # Constantes são deduplicadas: mesmo valor gera um único rótulo .data
    if tipo == "number":
        valor = no["valor"]
        if valor not in mapa_constantes:
            rotulo = f"const_{contador_constantes[0]}"
            mapa_constantes[valor] = rotulo
            contador_constantes[0] += 1
        else:
            rotulo = mapa_constantes[valor]

        linhas.append(f"    LDR r0, ={rotulo}")    # Endereço da constante
        linhas.append("    VLDR.F64 d0, [r0]")     # Carrega 64 bits para d0
        _emit_push_d0(linhas)                       # Empilha o operando
        return

    # (MEM) — leitura de variável de memória
    if tipo == "mem_read":
        mem = _normalizar_nome_mem(no["nome"])
        linhas.append(f"    LDR r0, =mem_{mem}")    # Endereço da variável
        linhas.append("    VLDR.F64 d0, [r0]")      # Carrega valor atual
        _emit_push_d0(linhas)
        return

    # (N RES) — referência a resultado de N linhas anteriores
    if tipo == "res_ref":
        alvo = indice_linha - no["linhas_atras"]
        if alvo < 0:
            alvo = 0
        linhas.append(f"    LDR r0, =resultado_{alvo}")  # Endereço do resultado
        linhas.append("    VLDR.F64 d0, [r0]")           # Carrega resultado
        _emit_push_d0(linhas)
        return

    # (V MEM) — escrita em memória
    # Avalia a sub-expressão V, desempilha e armazena em mem_*
    if tipo == "mem_write":
        _emit_expressao(no["valor"], linhas, mapa_constantes, contador_constantes, indice_linha)
        _emit_pop_para_d(linhas, "d0")
        mem = _normalizar_nome_mem(no["nome"])
        linhas.append(f"    LDR r0, =mem_{mem}")    # Endereço da variável
        linhas.append("    VSTR.F64 d0, [r0]")      # Armazena 64 bits
        _emit_push_d0(linhas)                        # Reempilha como resultado
        return

    # (A B op) — operação binária
    # Avalia operandos recursivamente (suporta aninhamento ilimitado),
    # desempilha dois valores e aplica o operador
    if tipo == "binary":
        _emit_expressao(no["esq"], linhas, mapa_constantes, contador_constantes, indice_linha)
        _emit_expressao(no["dir"], linhas, mapa_constantes, contador_constantes, indice_linha)
        _emit_pop_para_d(linhas, "d1")   # Operando direito (B) em d1
        _emit_pop_para_d(linhas, "d0")   # Operando esquerdo (A) em d0

        op = no["op"]
        # Operações com instruções nativas VFP (ponto flutuante 64 bits)
        if op == "+":
            linhas.append("    VADD.F64 d0, d0, d1")   # Adição
        elif op == "-":
            linhas.append("    VSUB.F64 d0, d0, d1")   # Subtração
        elif op == "*":
            linhas.append("    VMUL.F64 d0, d0, d1")   # Multiplicação
        elif op == "/":
            linhas.append("    VDIV.F64 d0, d0, d1")   # Divisão real
        # Operações com rotinas auxiliares (convertem para inteiro S32)
        elif op == "//":
            linhas.append("    BL __op_idiv")           # Divisão inteira
        elif op == "%":
            linhas.append("    BL __op_mod")            # Resto da divisão
        elif op == "^":
            linhas.append("    BL __op_pow")            # Potência
        else:
            raise ValueError(f"Operador não suportado: {op}")

        _emit_push_d0(linhas)   # Empilha resultado da operação
        return

    raise ValueError(f"Nó inválido: {tipo}")



# Função principal de geração — monta o Assembly ARMv7 completo


def gerar_assembly_armv7(arvores: list[dict]) -> str:
    """Gera código Assembly ARMv7 completo para todas as expressões.

    O código gerado inclui:
        - Diretivas de configuração (.syntax unified, .cpu cortex-a9, .fpu vfpv3)
        - Seção .text com instruções executáveis
        - Rotinas auxiliares: __op_idiv, __op_mod, __op_pow, __sdiv32
        - Rotina __exibir_hex para display HEX do DE1-SoC (0xFF200020)
        - Seção .data com constantes, variáveis de memória e resultados

    O resultado de cada expressão é exibido no display HEX3–HEX0
    da placa DE1-SoC.

    Args:
        arvores — lista de ASTs (uma por linha do arquivo de entrada)

    Returns:
        String com o código Assembly ARMv7 completo e funcional.
    """
    # Coleta todas as variáveis de memória para pré-declará-las na seção .data
    memorias: set[str] = set()
    for arvore in arvores:
        _coletar_memorias(arvore, memorias)

    # =================================================================
    # Seção .text — diretivas de configuração para ARMv7 DE1-SoC v16.1
    # =================================================================
    linhas: list[str] = []
    linhas.append(".syntax unified")    # Sintaxe ARM unificada (UAL)
    linhas.append(".cpu cortex-a9")     # Processador do DE1-SoC
    linhas.append(".fpu vfpv3")         # FPU com suporte a F64 (IEEE 754)
    linhas.append(".global _start")     # Ponto de entrada do programa
    linhas.append("")
    linhas.append(".text")
    linhas.append("_start:")

    # Mapa de constantes para deduplicação (mesmo valor = mesmo rótulo)
    mapa_constantes: dict[str, str] = {}
    contador_constantes = [0]  # Lista para permitir mutação dentro da recursão

    # Gera instruções para cada expressão do arquivo de entrada
    for indice, arvore in enumerate(arvores):
        linhas.append(f"    @ Expressão {indice + 1}")
        # Emite instruções recursivamente para a AST
        _emit_expressao(arvore, linhas, mapa_constantes, contador_constantes, indice)
        # Desempilha o resultado final da expressão para d0
        _emit_pop_para_d(linhas, "d0")
        # Armazena resultado na variável resultado_N (.data)
        linhas.append(f"    LDR r0, =resultado_{indice}")
        linhas.append("    VSTR.F64 d0, [r0]")
        # Exibe no display HEX do DE1-SoC
        linhas.append(f"    @ Exibir resultado {indice + 1} nos HEX displays")
        linhas.append("    VCVT.S32.F64 s0, d0")  # Converte F64 → inteiro S32
        linhas.append("    VMOV r0, s0")           # Move para registrador ARM
        linhas.append("    BL __exibir_hex")        # Chama rotina de exibição

    # Loop infinito após execução (padrão bare-metal ARMv7)
    linhas.append("")
    linhas.append("loop_final:")
    linhas.append("    B loop_final")

    # =================================================================
    # Rotinas auxiliares — operações que não possuem instrução nativa VFP
    # =================================================================

    # --- __op_idiv: Divisão inteira // ---
    # Converte F64 → S32, realiza divisão inteira via __sdiv32,
    # converte resultado S32 → F64
    linhas.append("")
    linhas.append("__op_idiv:")
    linhas.append("    @ Entrada: d0 (A), d1 (B)")
    linhas.append("    @ Saída: d0 = floor(A/B) usando divisão inteira em S32")
    linhas.append("    PUSH {lr}")
    linhas.append("    VCVT.S32.F64 s0, d0")
    linhas.append("    VCVT.S32.F64 s2, d1")
    linhas.append("    VMOV r0, s0")
    linhas.append("    VMOV r1, s2")
    linhas.append("    BL __sdiv32")
    linhas.append("    VMOV s0, r0")
    linhas.append("    VCVT.F64.S32 d0, s0")
    linhas.append("    POP {lr}")
    linhas.append("    BX lr")

    # --- __op_mod: Resto da divisão inteira % ---
    # Calcula A % B = A - (A // B) * B usando aritmética inteira S32
    linhas.append("")
    linhas.append("__op_mod:")
    linhas.append("    @ Entrada: d0 (A), d1 (B)")
    linhas.append("    @ Saída: d0 = A % B usando aritmética inteira S32")
    linhas.append("    PUSH {r4, lr}")
    linhas.append("    VCVT.S32.F64 s0, d0")
    linhas.append("    VCVT.S32.F64 s2, d1")
    linhas.append("    VMOV r2, s0")
    linhas.append("    VMOV r3, s2")
    linhas.append("    MOV r0, r2")
    linhas.append("    MOV r1, r3")
    linhas.append("    BL __sdiv32")
    linhas.append("    MUL r4, r0, r3")
    linhas.append("    SUB r2, r2, r4")
    linhas.append("    VMOV s0, r2")
    linhas.append("    VCVT.F64.S32 d0, s0")
    linhas.append("    POP {r4, lr}")
    linhas.append("    BX lr")

    # --- __op_pow: Potência ^ ---
    # base ^ expoente por multiplicação iterativa (expoente inteiro positivo)
    # Retorna 1.0 se expoente <= 0
    linhas.append("")
    linhas.append("__op_pow:")
    linhas.append("    @ Entrada: d0 (base), d1 (expoente inteiro positivo)")
    linhas.append("    @ Saída: d0 = base ^ expoente")
    linhas.append("    PUSH {lr}")
    linhas.append("    VCVT.S32.F64 s2, d1")
    linhas.append("    VMOV r3, s2")
    linhas.append("    CMP r3, #0")
    linhas.append("    BLE __pow_zero_ou_negativo")
    linhas.append("    VMOV.F64 d2, d0")
    linhas.append("    SUB r3, r3, #1")
    linhas.append("__pow_loop:")
    linhas.append("    CMP r3, #0")
    linhas.append("    BEQ __pow_done")
    linhas.append("    VMUL.F64 d2, d2, d0")
    linhas.append("    SUB r3, r3, #1")
    linhas.append("    B __pow_loop")
    linhas.append("__pow_done:")
    linhas.append("    VMOV.F64 d0, d2")
    linhas.append("    POP {lr}")
    linhas.append("    BX lr")
    linhas.append("__pow_zero_ou_negativo:")
    linhas.append("    LDR r0, =const_one")
    linhas.append("    VLDR.F64 d0, [r0]")
    linhas.append("    POP {lr}")
    linhas.append("    BX lr")

    # --- __sdiv32: Divisão inteira com sinal (subtração iterativa) ---
    # Usada por __op_idiv e __op_mod. Normaliza sinais, faz loop de
    # subtração e restaura sinal. Retorna 0 em divisão por zero.
    linhas.append("")
    linhas.append("__sdiv32:")
    linhas.append("    @ Entrada: r0 numerador, r1 denominador")
    linhas.append("    @ Saída: r0 quociente (divisão inteira com sinal)")
    linhas.append("    PUSH {r2, r3, r4, lr}")
    linhas.append("    CMP r1, #0")
    linhas.append("    BEQ __sdiv32_divzero")
    linhas.append("    MOV r2, #0")
    linhas.append("    CMP r0, #0")
    linhas.append("    RSBMI r0, r0, #0")
    linhas.append("    EORMI r2, r2, #1")
    linhas.append("    CMP r1, #0")
    linhas.append("    RSBMI r1, r1, #0")
    linhas.append("    EORMI r2, r2, #1")
    linhas.append("    MOV r3, #0")
    linhas.append("__sdiv32_loop:")
    linhas.append("    CMP r0, r1")
    linhas.append("    BLT __sdiv32_done")
    linhas.append("    SUB r0, r0, r1")
    linhas.append("    ADD r3, r3, #1")
    linhas.append("    B __sdiv32_loop")
    linhas.append("__sdiv32_done:")
    linhas.append("    CMP r2, #0")
    linhas.append("    RSBNE r3, r3, #0")
    linhas.append("    MOV r0, r3")
    linhas.append("    POP {r2, r3, r4, lr}")
    linhas.append("    BX lr")
    linhas.append("__sdiv32_divzero:")
    linhas.append("    MOV r0, #0")
    linhas.append("    POP {r2, r3, r4, lr}")
    linhas.append("    BX lr")

    # --- __exibir_hex: Exibição no display HEX do DE1-SoC ---
    # Decompõe valor inteiro em até 4 dígitos decimais, consulta tabela
    # de 7 segmentos e escreve no endereço 0xFF200020 (HEX3–HEX0).
    # Suporta valores negativos (exibe '-' no dígito mais significativo).
    linhas.append("")
    linhas.append("__exibir_hex:")
    linhas.append("    @ Entrada: r0 = valor inteiro (parte inteira do resultado)")
    linhas.append("    @ Exibe nos HEX displays do DE1-SoC (endereço 0xFF200020)")
    linhas.append("    PUSH {r1, r2, r3, r4, r5, r6, lr}")
    linhas.append("    LDR r1, =__hex_tabela")
    linhas.append("    LDR r6, =0xFF200020      @ HEX3-HEX0")
    linhas.append("    @ Verificar se negativo")
    linhas.append("    MOV r5, #0               @ flag negativo")
    linhas.append("    CMP r0, #0")
    linhas.append("    RSBMI r0, r0, #0")
    linhas.append("    MOVMI r5, #1")
    linhas.append("    MOV r4, #0               @ resultado acumulado para HEX")
    linhas.append("    @ Dígito 0 (unidades)")
    linhas.append("    MOV r2, #10")
    linhas.append("    BL __udiv_simples")
    linhas.append("    LDRB r3, [r1, r3]        @ r3 = resto da divisão anterior")
    linhas.append("    ORR r4, r4, r3")
    linhas.append("    @ Dígito 1 (dezenas)")
    linhas.append("    MOV r2, #10")
    linhas.append("    BL __udiv_simples")
    linhas.append("    LDRB r3, [r1, r3]")
    linhas.append("    ORR r4, r4, r3, LSL #8")
    linhas.append("    @ Dígito 2 (centenas)")
    linhas.append("    MOV r2, #10")
    linhas.append("    BL __udiv_simples")
    linhas.append("    LDRB r3, [r1, r3]")
    linhas.append("    ORR r4, r4, r3, LSL #16")
    linhas.append("    @ Dígito 3 (sinal ou milhares)")
    linhas.append("    CMP r5, #1")
    linhas.append("    MOVEQ r3, #0x40          @ segmento '-' (segmento g)") 
    linhas.append("    BEQ __exibir_hex_store")
    linhas.append("    MOV r2, #10")
    linhas.append("    BL __udiv_simples")
    linhas.append("    LDRB r3, [r1, r3]")
    linhas.append("    ORR r4, r4, r3, LSL #24")
    linhas.append("    B __exibir_hex_fim")
    linhas.append("__exibir_hex_store:")
    linhas.append("    ORR r4, r4, r3, LSL #24")
    linhas.append("__exibir_hex_fim:")
    linhas.append("    STR r4, [r6]")
    linhas.append("    POP {r1, r2, r3, r4, r5, r6, lr}")
    linhas.append("    BX lr")

    # --- __udiv_simples: Divisão sem sinal por subtração (para display HEX) ---
    linhas.append("")
    linhas.append("__udiv_simples:")
    linhas.append("    @ r0 / r2 -> r0 = quociente, r3 = resto")
    linhas.append("    MOV r3, #0")
    linhas.append("__udiv_simples_loop:")
    linhas.append("    CMP r0, r2")
    linhas.append("    BLT __udiv_simples_done")
    linhas.append("    SUB r0, r0, r2")
    linhas.append("    ADD r3, r3, #1")
    linhas.append("    B __udiv_simples_loop")
    linhas.append("__udiv_simples_done:")
    linhas.append("    @ r3 = quociente, r0 = resto")
    linhas.append("    MOV r12, r0              @ salva resto em r12")
    linhas.append("    MOV r0, r3               @ r0 = quociente")
    linhas.append("    MOV r3, r12              @ r3 = resto")
    linhas.append("    BX lr")
    linhas.append("")

    # =================================================================
    # Seção .data — constantes, variáveis de memória e resultados
    # Todos os valores são .double (IEEE 754 64 bits)
    # =================================================================
    linhas.append(".data")

    # Constantes numéricas (deduplicadas)
    for valor, rotulo in mapa_constantes.items():
        linhas.append(f"{rotulo}: .double {valor}")

    # Constante 1.0 usada pela rotina de potência (__op_pow)
    linhas.append("const_one: .double 1.0")

    # Variáveis de memória: inicializadas em 0.0
    for mem in sorted(memorias):
        linhas.append(f"mem_{mem}: .double 0.0")

    # Resultado de cada linha — armazena o valor calculado
    for indice in range(len(arvores)):
        linhas.append(f"resultado_{indice}: .double 0.0")

    if not arvores:
        linhas.append("resultado_0: .double 0.0")  # Fallback para entrada vazia

    # Tabela de 7 segmentos para display HEX (dígitos 0–9)
    # Cada byte mapeia um dígito ao padrão de segmentos a–g do display
    linhas.append("")
    linhas.append("@ Tabela de segmentos para display HEX (0-9)")
    linhas.append("__hex_tabela:")
    linhas.append("    .byte 0x3F  @ 0")
    linhas.append("    .byte 0x06  @ 1")
    linhas.append("    .byte 0x5B  @ 2")
    linhas.append("    .byte 0x4F  @ 3")
    linhas.append("    .byte 0x66  @ 4")
    linhas.append("    .byte 0x6D  @ 5")
    linhas.append("    .byte 0x7D  @ 6")
    linhas.append("    .byte 0x07  @ 7")
    linhas.append("    .byte 0x7F  @ 8")
    linhas.append("    .byte 0x6F  @ 9")

    return "\n".join(linhas) + "\n"
