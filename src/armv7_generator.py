# Integrantes:
#   Arthur Felipe Bach Biancolini
#   Emanuel Riceto da Silva
#   Frederico Virmond Fruet
#   Pedro Alessandrini Braiti
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

from typing import Dict, List, Tuple, Set


def _normalizar_nome_mem(nome: str) -> str:
    return nome.lower()


def _coletar_memorias(no: Dict, memorias: Set[str]) -> None:
    tipo = no["tipo"]
    if tipo == "mem_write":
        memorias.add(_normalizar_nome_mem(no["nome"]))
        _coletar_memorias(no["valor"], memorias)
    elif tipo == "mem_read":
        memorias.add(_normalizar_nome_mem(no["nome"]))
    elif tipo == "binary":
        _coletar_memorias(no["esq"], memorias)
        _coletar_memorias(no["dir"], memorias)


def _emit_push_d0(linhas: List[str]) -> None:
    linhas.append("    VMOV r4, r5, d0")
    linhas.append("    PUSH {r4, r5}")


def _emit_pop_para_d(linhas: List[str], reg_d: str) -> None:
    linhas.append("    POP {r4, r5}")
    linhas.append(f"    VMOV {reg_d}, r4, r5")


def _emit_expressao(
    no: Dict,
    linhas: List[str],
    mapa_constantes: Dict[str, str],
    contador_constantes: List[int],
    indice_linha: int,
) -> None:
    tipo = no["tipo"]

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

    if tipo == "mem_read":
        mem = _normalizar_nome_mem(no["nome"])
        linhas.append(f"    LDR r0, =mem_{mem}")
        linhas.append("    VLDR.F64 d0, [r0]")
        _emit_push_d0(linhas)
        return

    if tipo == "res_ref":
        alvo = indice_linha - no["linhas_atras"]
        if alvo < 0:
            alvo = 0
        linhas.append(f"    LDR r0, =resultado_{alvo}")
        linhas.append("    VLDR.F64 d0, [r0]")
        _emit_push_d0(linhas)
        return

    if tipo == "mem_write":
        _emit_expressao(no["valor"], linhas, mapa_constantes, contador_constantes, indice_linha)
        _emit_pop_para_d(linhas, "d0")
        mem = _normalizar_nome_mem(no["nome"])
        linhas.append(f"    LDR r0, =mem_{mem}")
        linhas.append("    VSTR.F64 d0, [r0]")
        _emit_push_d0(linhas)
        return

    if tipo == "binary":
        _emit_expressao(no["esq"], linhas, mapa_constantes, contador_constantes, indice_linha)
        _emit_expressao(no["dir"], linhas, mapa_constantes, contador_constantes, indice_linha)
        _emit_pop_para_d(linhas, "d1")
        _emit_pop_para_d(linhas, "d0")

        op = no["op"]
        if op == "+":
            linhas.append("    VADD.F64 d0, d0, d1")
        elif op == "-":
            linhas.append("    VSUB.F64 d0, d0, d1")
        elif op == "*":
            linhas.append("    VMUL.F64 d0, d0, d1")
        elif op == "/":
            linhas.append("    VDIV.F64 d0, d0, d1")
        else:
            raise ValueError(f"Operador não suportado: {op}")

        _emit_push_d0(linhas)
        return

    raise ValueError(f"Nó inválido: {tipo}")


def gerar_assembly_armv7(arvores: List[Dict]) -> str:
    memorias: Set[str] = set()
    for arvore in arvores:
        _coletar_memorias(arvore, memorias)

    linhas: List[str] = []
    linhas.append(".syntax unified")
    linhas.append(".cpu cortex-a9")
    linhas.append(".fpu vfpv3")
    linhas.append(".global _start")
    linhas.append("")
    linhas.append(".text")
    linhas.append("_start:")

    mapa_constantes: Dict[str, str] = {}
    contador_constantes = [0]

    for indice, arvore in enumerate(arvores):
        linhas.append(f"    @ Expressão {indice + 1}")
        _emit_expressao(arvore, linhas, mapa_constantes, contador_constantes, indice)
        _emit_pop_para_d(linhas, "d0")
        linhas.append(f"    LDR r0, =resultado_{indice}")
        linhas.append("    VSTR.F64 d0, [r0]")

    linhas.append("")
    linhas.append("loop_final:")
    linhas.append("    B loop_final")

    linhas.append("")
    linhas.append(".data")
    for valor, rotulo in mapa_constantes.items():
        linhas.append(f"{rotulo}: .double {valor}")

    linhas.append("const_one: .double 1.0")

    for mem in sorted(memorias):
        linhas.append(f"mem_{mem}: .double 0.0")

    for indice in range(len(arvores)):
        linhas.append(f"resultado_{indice}: .double 0.0")

    if not arvores:
        linhas.append("resultado_0: .double 0.0")

    return "\n".join(linhas) + "\n"
