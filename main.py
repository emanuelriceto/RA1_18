# Integrantes:
#   Arthur Felipe Bach Biancolini (Tuizones)
#   Emanuel Riceto da Silva (emanuelriceto)
#   Frederico Virmond Fruet (fredfruet)
#   Pedro Alessandrini Braiti (pedrobraiti)
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

# Implementa a interface do programa via linha de comando:
#   python main.py teste1.txt
# O nome do arquivo de teste é recebido como argumento de linha de comando.
# Pipeline de execução:
#   1. lerArquivo     — lê o arquivo de expressões RPN
#   2. parseExpressao — tokeniza cada linha via AFD (análise léxica)
#   3. executarExpressao — valida semântica (sem realizar cálculos)
#   4. gerarAssembly  — gera código Assembly ARMv7 para CPUlator DE1-SoC
#   5. exibirResultados — exibe descrições no console
# Saídas geradas:
#   - output/ultima_execucao.s            — código Assembly ARMv7
#   - output/tokens_ultima_execucao.txt   — tokens da última execução

import argparse
from pathlib import Path

from src.pipeline import parseExpressao, executarExpressao, gerarAssembly, exibirResultados, lerArquivo


def _salvar_tokens(caminho: Path, tokens_por_linha) -> None:
    """Salva os tokens da última execução em arquivo texto.

    O vetor de tokens gerado pelo analisador léxico deve ser salvo
    em arquivo .txt. Formato: TIPO:valor por token.
    Apenas os tokens da última execução ficam no repositório.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arquivo:
        for i, tokens in enumerate(tokens_por_linha, start=1):
            pares = [f"{t.tipo}:{t.valor}" for t in tokens]
            arquivo.write(f"linha_{i};" + ",".join(pares) + "\n")


def main() -> None:
    """Função principal — orquestra o pipeline completo.

    Recebe o arquivo de teste via argumento de linha de comando,
    executa as 5 funções obrigatórias em sequência, e salva as saídas.
    """
    parser = argparse.ArgumentParser(description="Léxico + Assembly ARMv7")
    parser.add_argument("arquivo", help="Arquivo de teste com expressões RPN")
    parser.add_argument("--out", default="output/ultima_execucao.s", help="Arquivo Assembly de saída")
    parser.add_argument(
        "--tokens-out",
        default="output/tokens_ultima_execucao.txt",
        help="Arquivo de saída para tokens da última execução",
    )
    args = parser.parse_args()

    # lerArquivo: lê expressões RPN do arquivo
    linhas: list[str] = []
    lerArquivo(args.arquivo, linhas)

    # Contexto compartilhado entre expressões: memória e histórico
    contexto = {"memoria": {}, "resultados": []}
    resultados = []
    tokens_por_linha_obj = []
    tokens_por_linha_str = []

    # parseExpressao + executarExpressao para cada linha
    for linha in linhas:
        tokens_linha: list[str] = []
        # análise léxica via AFD
        tokens_obj = parseExpressao(linha, tokens_linha)
        # validação semântica sem realizar cálculos
        exec_result = executarExpressao(tokens_obj, contexto)
        resultados.append(exec_result)
        tokens_por_linha_obj.append(tokens_obj)
        tokens_por_linha_str.append(tokens_linha)

    #  gerarAssembly: gera código ARMv7 para CPUlator
    assembly = gerarAssembly(tokens_por_linha_obj)

    # Salva Assembly gerado (última versão no repositório)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(assembly, encoding="utf-8")

    # Salva tokens da última execução
    _salvar_tokens(Path(args.tokens_out), tokens_por_linha_obj)

    exibirResultados(resultados)
    print(f"\nAssembly gerado em: {out_path}")
    print(f"Tokens salvos em: {Path(args.tokens_out)}")


if __name__ == "__main__":
    main()
