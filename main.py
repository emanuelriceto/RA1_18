# Integrantes:
#   Arthur Felipe Bach Biancolini (Tuizones)
#   Emanuel Riceto da Silva (emanuelriceto)
#   Frederico Virmond Fruet (fredfruet)
#   Pedro Alessandrini Braiti (pedrobraiti)
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

# Ponto de entrada do programa. Recebe o arquivo de teste por argumento
# e roda o pipeline: ler arquivo -> tokenizar -> validar -> gerar assembly -> exibir.
# Uso: python main.py teste1.txt

import argparse
from pathlib import Path

from src.pipeline import parseExpressao, executarExpressao, gerarAssembly, exibirResultados, lerArquivo


def _salvar_tokens(caminho: Path, tokens_por_linha) -> None:
    """Salva tokens no .txt (formato TIPO:valor)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arquivo:
        for i, tokens in enumerate(tokens_por_linha, start=1):
            pares = [f"{t.tipo}:{t.valor}" for t in tokens]
            arquivo.write(f"linha_{i};" + ",".join(pares) + "\n")


def main() -> None:
    """Roda o pipeline completo: leitura -> léxico -> semântica -> assembly -> saída."""
    parser = argparse.ArgumentParser(description="Léxico + Assembly ARMv7")
    parser.add_argument("arquivo", help="Arquivo de teste com expressões RPN")
    parser.add_argument("--out", default="output/ultima_execucao.s", help="Arquivo Assembly de saída")
    parser.add_argument(
        "--tokens-out",
        default="output/tokens_ultima_execucao.txt",
        help="Arquivo de saída para tokens da última execução",
    )
    args = parser.parse_args()

    linhas: list[str] = []
    lerArquivo(args.arquivo, linhas)

    contexto = {"memoria": {}, "resultados": []}
    resultados = []
    tokens_por_linha_obj = []
    tokens_por_linha_str = []

    for linha in linhas:
        tokens_linha: list[str] = []
        tokens_obj = parseExpressao(linha, tokens_linha)
        exec_result = executarExpressao(tokens_obj, contexto)
        resultados.append(exec_result)
        tokens_por_linha_obj.append(tokens_obj)
        tokens_por_linha_str.append(tokens_linha)

    assembly = gerarAssembly(tokens_por_linha_obj)

    # salva o .s e o .txt de tokens
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(assembly, encoding="utf-8")
    _salvar_tokens(Path(args.tokens_out), tokens_por_linha_obj)

    exibirResultados(resultados)
    print(f"\nAssembly gerado em: {out_path}")
    print(f"Tokens salvos em: {Path(args.tokens_out)}")


if __name__ == "__main__":
    main()
