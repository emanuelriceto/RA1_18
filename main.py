# Integrantes:
#   Arthur Felipe Bach Biancolini
#   Emanuel Riceto da Silva
#   Frederico Virmond Fruet
#   Pedro Alessandrini Braiti
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

import argparse
from pathlib import Path
from typing import List

from src.pipeline import parseExpressao, executarExpressao, exibirResultados, lerArquivo


def main() -> None:
    parser = argparse.ArgumentParser(description="Fase 1: Léxico + Assembly ARMv7 para RPN")
    parser.add_argument("arquivo", help="Arquivo de teste com expressões RPN")
    args = parser.parse_args()

    linhas: List[str] = []
    lerArquivo(args.arquivo, linhas)

    contexto = {"memoria": {}, "resultados": []}
    resultados = []

    for linha in linhas:
        tokens_linha: List[str] = []
        tokens_obj = parseExpressao(linha, tokens_linha)
        exec_result = executarExpressao(tokens_obj, contexto)
        resultados.append(exec_result)

    exibirResultados(resultados)


if __name__ == "__main__":
    main()
