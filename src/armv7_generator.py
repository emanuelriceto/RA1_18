# Integrantes:
#   Arthur Felipe Bach Biancolini (Tuizones)
#   Emanuel Riceto da Silva (emanuelriceto)
#   Frederico Virmond Fruet (fredfruet)
#   Pedro Alessandrini Braiti (pedrobraiti)
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

# Gerador de Assembly ARMv7 pra rodar no CPUlator (DE1-SoC).
# Usa pilha pra empilhar/desempilhar operandos em ponto flutuante 64 bits.
# Resultado aparece no display HEX da placa (0xFF200020).




def _normalizar_nome_mem(nome: str) -> str:
    return nome.lower()


def _coletar_memorias(no: dict, memorias: set[str]) -> None:
    """Percorre a AST coletando nomes de variáveis MEM pra declarar no .data."""
    tipo = no["tipo"]
    if tipo == "mem_write":
        memorias.add(_normalizar_nome_mem(no["nome"]))
        _coletar_memorias(no["valor"], memorias)
    elif tipo == "mem_read":
        memorias.add(_normalizar_nome_mem(no["nome"]))
    elif tipo == "binary":
        _coletar_memorias(no["esq"], memorias)
        _coletar_memorias(no["dir"], memorias)



# Como empilhar/desempilhar doubles de 64 bits na pilha ARM:
# VMOV r4,r5,d0 + PUSH {r4,r5}  -> empilha
# POP {r4,r5} + VMOV dN,r4,r5   -> desempilha


def _emit_push_d0(linhas: list[str]) -> None:
    """Empilha d0."""
    linhas.append("    VMOV r4, r5, d0")
    linhas.append("    PUSH {r4, r5}")


def _emit_pop_para_d(linhas: list[str], reg_d: str) -> None:
    """Desempilha pra registrador FP."""
    linhas.append("    POP {r4, r5}")
    linhas.append(f"    VMOV {reg_d}, r4, r5")



# Emissão recursiva de instruções pra cada nó da AST


def _emit_expressao(
    no: dict,
    linhas: list[str],
    mapa_constantes: dict[str, str],
    contador_constantes: list[int],
    indice_linha: int,
) -> None:
    """Gera instruções Assembly pro nó da AST (recursivo)."""
    tipo = no["tipo"]

    # numero literal -> carrega constante do .data
    # constantes iguais são reaproveitadas (deduplicacao)
    if tipo == "number":
        valor = no["valor"]
        if valor not in mapa_constantes:
            rotulo = f"const_{contador_constantes[0]}"
            mapa_constantes[valor] = rotulo
            contador_constantes[0] += 1
        else:
            rotulo = mapa_constantes[valor]

        linhas.append(f"    LDR r0, ={rotulo}")
        linhas.append("    VLDR.F64 d0, [r0]")
        _emit_push_d0(linhas)
        return

    # leitura de variavel de memoria
    if tipo == "mem_read":
        mem = _normalizar_nome_mem(no["nome"])
        linhas.append(f"    LDR r0, =mem_{mem}")
        linhas.append("    VLDR.F64 d0, [r0]")
        _emit_push_d0(linhas)
        return

    # referencia a resultado de outra linha
    if tipo == "res_ref":
        alvo = indice_linha - no["linhas_atras"]
        if alvo < 0:
            alvo = 0
        linhas.append(f"    LDR r0, =resultado_{alvo}")
        linhas.append("    VLDR.F64 d0, [r0]")
        _emit_push_d0(linhas)
        return

    # escrita em memoria
    if tipo == "mem_write":
        _emit_expressao(no["valor"], linhas, mapa_constantes, contador_constantes, indice_linha)
        _emit_pop_para_d(linhas, "d0")
        mem = _normalizar_nome_mem(no["nome"])
        linhas.append(f"    LDR r0, =mem_{mem}")
        linhas.append("    VSTR.F64 d0, [r0]")
        _emit_push_d0(linhas)
        return

    # operacao binaria (A B op)
    if tipo == "binary":
        _emit_expressao(no["esq"], linhas, mapa_constantes, contador_constantes, indice_linha)
        _emit_expressao(no["dir"], linhas, mapa_constantes, contador_constantes, indice_linha)
        _emit_pop_para_d(linhas, "d1")   # direito
        _emit_pop_para_d(linhas, "d0")   # esquerdo

        op = no["op"]
        # operações nativas VFP
        if op == "+":
            linhas.append("    VADD.F64 d0, d0, d1")
        elif op == "-":
            linhas.append("    VSUB.F64 d0, d0, d1")
        elif op == "*":
            linhas.append("    VMUL.F64 d0, d0, d1")
        elif op == "/":
            linhas.append("    VDIV.F64 d0, d0, d1")
        # essas precisam de rotinas auxiliares
        elif op == "//":
            linhas.append("    BL __op_idiv")
        elif op == "%":
            linhas.append("    BL __op_mod")
        elif op == "^":
            linhas.append("    BL __op_pow")
        else:
            raise ValueError(f"Operador não suportado: {op}")

        _emit_push_d0(linhas)
        return

    raise ValueError(f"Nó inválido: {tipo}")


def gerar_assembly_armv7(arvores: list[dict]) -> str:
    """Gera o Assembly ARMv7 completo (.text + rotinas auxiliares + .data)."""
    # coleta variaveis de memoria pra declarar no .data
    memorias: set[str] = set()
    for arvore in arvores:
        _coletar_memorias(arvore, memorias)

    # .text - diretivas do ARMv7
    linhas: list[str] = []
    linhas.append(".syntax unified")
    linhas.append(".cpu cortex-a9")
    linhas.append(".fpu vfpv3")
    linhas.append(".global _start")
    linhas.append("")
    linhas.append(".text")
    linhas.append("_start:")

    # mapa pra deduplicar constantes
    mapa_constantes: dict[str, str] = {}
    contador_constantes = [0]  # lista pra poder mutar na recursao

    # gera instrucoes pra cada expressao
    for indice, arvore in enumerate(arvores):
        linhas.append(f"    @ Expressão {indice + 1}")
        _emit_expressao(arvore, linhas, mapa_constantes, contador_constantes, indice)
        _emit_pop_para_d(linhas, "d0")
        # salva resultado
        linhas.append(f"    LDR r0, =resultado_{indice}")
        linhas.append("    VSTR.F64 d0, [r0]")
        # mostra no display HEX
        linhas.append(f"    @ Exibir resultado {indice + 1} nos HEX displays")
        linhas.append("    VCVT.S32.F64 s0, d0")
        linhas.append("    VMOV r0, s0")
        linhas.append("    BL __exibir_hex")

    # loop infinito (padrao bare-metal)
    linhas.append("")
    linhas.append("loop_final:")
    linhas.append("    B loop_final")

    # --- Rotinas auxiliares ---

    # divisao inteira //: F64 -> S32, divide, S32 -> F64
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

    # resto: A % B = A - (A//B)*B
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

    # potencia: base^exp por multiplicacao iterativa
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

    # divisao inteira com sinal (subtracao iterativa)
    # usada pelo idiv e mod
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

    # exibicao no display HEX: decompoe em digitos e usa tabela de 7 segmentos
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

    # divisao sem sinal simples (usada pelo exibir_hex)
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

    # .data - constantes, variaveis de memoria e resultados
    linhas.append(".data")

    # constantes numericas
    for valor, rotulo in mapa_constantes.items():
        linhas.append(f"{rotulo}: .double {valor}")

    # 1.0 pro __op_pow
    linhas.append("const_one: .double 1.0")

    # variaveis de memoria
    for mem in sorted(memorias):
        linhas.append(f"mem_{mem}: .double 0.0")

    # resultado de cada linha
    for indice in range(len(arvores)):
        linhas.append(f"resultado_{indice}: .double 0.0")

    if not arvores:
        linhas.append("resultado_0: .double 0.0")

    # tabela 7 segmentos pro display HEX (0-9)
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
