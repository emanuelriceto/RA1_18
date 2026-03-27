# Integrantes:
#   Arthur Felipe Bach Biancolini (Tuizones)
#   Emanuel Riceto da Silva (emanuelriceto)
#   Frederico Virmond Fruet (fredfruet)
#   Pedro Alessandrini Braiti (pedrobraiti)
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

import os
import unittest
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline import parseExpressao, executarExpressao, gerarAssembly, lerArquivo, Erros


class TestPipeline(unittest.TestCase):
    def test_fluxo_completo_gera_rotinas_arm(self):
        linhas = [
            "(10 3 //)",
            "(10 3 %)",
            "(2 5 ^)",
            "(4.5 MEM)",
            "(MEM)",
            "(1 RES)",
        ]

        contexto = {"memoria": {}, "resultados": []}
        tokens_por_linha = []

        for linha in linhas:
            tokens_saida = []
            tokens = parseExpressao(linha, tokens_saida)
            executarExpressao(tokens, contexto)
            tokens_por_linha.append(tokens)

        assembly = gerarAssembly(tokens_por_linha)

        self.assertIn("__op_idiv:", assembly)
        self.assertIn("__sdiv32:", assembly)
        self.assertIn("__op_mod:", assembly)
        self.assertIn("__op_pow:", assembly)
        self.assertIn("mem_mem", assembly)
        self.assertIn("resultado_0", assembly)
        self.assertIn("__exibir_hex:", assembly)
        self.assertIn("0xFF200020", assembly)

    def test_res_invalido_dispara_erro(self):
        contexto = {"memoria": {}, "resultados": []}
        tokens_saida = []
        tokens = parseExpressao("(1 RES)", tokens_saida)

        with self.assertRaises(Erros):
            executarExpressao(tokens, contexto)

    def test_parseExpressao_retorna_tokens_str(self):
        tokens_saida = []
        parseExpressao("(3.0 2.0 +)", tokens_saida)
        self.assertEqual(tokens_saida, ["(", "3.0", "2.0", "+", ")"])

    def test_executarExpressao_expressao_simples(self):
        contexto = {"memoria": {}, "resultados": []}
        tokens_saida = []
        tokens = parseExpressao("(3.0 2.0 +)", tokens_saida)
        resultado = executarExpressao(tokens, contexto)
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["descricao"], "expressão válida")

    def test_executarExpressao_mem_write(self):
        contexto = {"memoria": {}, "resultados": []}
        tokens_saida = []
        tokens = parseExpressao("(5.0 VARA)", tokens_saida)
        resultado = executarExpressao(tokens, contexto)
        self.assertIn("VARA", contexto["memoria"])

    def test_executarExpressao_mem_read(self):
        contexto = {"memoria": {}, "resultados": []}
        tokens_saida = []
        tokens = parseExpressao("(TEMP)", tokens_saida)
        resultado = executarExpressao(tokens, contexto)
        self.assertIn("leitura", resultado["descricao"])

    def test_executarExpressao_res_valido(self):
        contexto = {"memoria": {}, "resultados": ["r1", "r2"]}
        tokens_saida = []
        tokens = parseExpressao("(1 RES)", tokens_saida)
        resultado = executarExpressao(tokens, contexto)
        self.assertTrue(resultado["ok"])

    def test_gerarAssembly_todas_operacoes(self):
        linhas = [
            "(1.0 2.0 +)",
            "(3.0 1.0 -)",
            "(2.0 3.0 *)",
            "(6.0 2.0 /)",
            "(7 3 //)",
            "(7 3 %)",
            "(2 4 ^)",
        ]
        contexto = {"memoria": {}, "resultados": []}
        tokens_por_linha = []
        for linha in linhas:
            ts = []
            tokens = parseExpressao(linha, ts)
            executarExpressao(tokens, contexto)
            tokens_por_linha.append(tokens)

        assembly = gerarAssembly(tokens_por_linha)
        self.assertIn("VADD.F64", assembly)
        self.assertIn("VSUB.F64", assembly)
        self.assertIn("VMUL.F64", assembly)
        self.assertIn("VDIV.F64", assembly)
        self.assertIn("BL __op_idiv", assembly)
        self.assertIn("BL __op_mod", assembly)
        self.assertIn("BL __op_pow", assembly)

    def test_gerarAssembly_expressao_aninhada(self):
        contexto = {"memoria": {}, "resultados": []}
        tokens_saida = []
        tokens = parseExpressao("((3.0 2.0 +) (4.0 1.0 -) *)", tokens_saida)
        executarExpressao(tokens, contexto)
        assembly = gerarAssembly([tokens])
        self.assertIn("VADD.F64", assembly)
        self.assertIn("VSUB.F64", assembly)
        self.assertIn("VMUL.F64", assembly)

    def test_gerarAssembly_ieee754_64bits(self):
        contexto = {"memoria": {}, "resultados": []}
        tokens_saida = []
        tokens = parseExpressao("(3.14 2.0 +)", tokens_saida)
        executarExpressao(tokens, contexto)
        assembly = gerarAssembly([tokens])
        self.assertIn(".double", assembly)
        self.assertIn("F64", assembly)

    def test_lerArquivo_ignora_comentarios(self):
        import tempfile
        import os
        conteudo = "# comentario\n(1 2 +)\n\n(3 4 *)\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(conteudo)
            nome = f.name
        try:
            linhas = []
            lerArquivo(nome, linhas)
            self.assertEqual(linhas, ["(1 2 +)", "(3 4 *)"])
        finally:
            os.unlink(nome)


if __name__ == "__main__":
    unittest.main()
