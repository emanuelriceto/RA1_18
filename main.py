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

from src.pipeline import parseExpressao, executarExpressao, gerarAssembly, exibirResultados, lerArquivo


def _salvar_tokens(caminho: Path, tokens_por_linha) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arquivo:
        for i, tokens in enumerate(tokens_por_linha, start=1):
            pares = [f"{t.tipo}:{t.valor}" for t in tokens]
            arquivo.write(f"linha_{i};" + ",".join(pares) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fase 1: Léxico + Assembly ARMv7 para RPN")
    parser.add_argument("arquivo", help="Arquivo de teste com expressões RPN")
    parser.add_argument("--out", default="output/ultima_execucao.s", help="Arquivo Assembly de saída")
    parser.add_argument(
        "--tokens-out",
        default="output/tokens_ultima_execucao.txt",
        help="Arquivo de saída para tokens da última execução",
    )
    args = parser.parse_args()

    linhas: List[str] = []
    lerArquivo(args.arquivo, linhas)

    contexto = {"memoria": {}, "resultados": []}
    resultados = []
    tokens_por_linha_obj = []
    tokens_por_linha_str = []

    for linha in linhas:
        tokens_linha: List[str] = []
        tokens_obj = parseExpressao(linha, tokens_linha)
        exec_result = executarExpressao(tokens_obj, contexto)
        resultados.append(exec_result)
        tokens_por_linha_obj.append(tokens_obj)
        tokens_por_linha_str.append(tokens_linha)

    assembly = gerarAssembly(tokens_por_linha_obj)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(assembly, encoding="utf-8")

    _salvar_tokens(Path(args.tokens_out), tokens_por_linha_obj)

    exibirResultados(resultados)
    print(f"\nAssembly gerado em: {out_path}")
    print(f"Tokens salvos em: {Path(args.tokens_out)}")


if __name__ == "__main__":
    main()
