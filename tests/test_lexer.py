# Integrantes:
#   Arthur Felipe Bach Biancolini (Tuizones)
#   Emanuel Riceto da Silva (emanuelriceto)
#   Frederico Virmond Fruet (fredfruet)
#   Pedro Alessandrini Braiti (pedrobraiti)
# Grupo Canvas: RA1 18
# Instituição: Pontifícia Universidade Católica do Paraná
# Disciplina: Linguagens Formais e Compiladores
# Professor: Frank Coelho de Alcantara

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lexer_fsm import tokenizar_linha, Erros, TIPO_NUMERO, TIPO_OPERADOR, TIPO_ABRE, TIPO_FECHA, TIPO_IDENT, TIPO_KEYWORD


class TestLexerFSM(unittest.TestCase):

    def test_entrada_valida_simples(self):
        tokens = tokenizar_linha("(3.14 2.0 +)")
        valores = [t.valor for t in tokens]
        self.assertEqual(valores, ["(", "3.14", "2.0", "+", ")"])

    def test_entrada_valida_res(self):
        tokens = tokenizar_linha("(5 RES)")
        valores = [t.valor for t in tokens]
        self.assertEqual(valores, ["(", "5", "RES", ")"])

    def test_entrada_valida_memoria(self):
        tokens = tokenizar_linha("(10.5 CONTADOR)")
        valores = [t.valor for t in tokens]
        self.assertEqual(valores, ["(", "10.5", "CONTADOR", ")"])

    def test_operador_subtracao(self):
        tokens = tokenizar_linha("(10.0 4.0 -)")
        valores = [t.valor for t in tokens]
        self.assertEqual(valores, ["(", "10.0", "4.0", "-", ")"])

    def test_operador_multiplicacao(self):
        tokens = tokenizar_linha("(2.5 8.0 *)")
        valores = [t.valor for t in tokens]
        self.assertEqual(valores, ["(", "2.5", "8.0", "*", ")"])

    def test_operador_divisao(self):
        tokens = tokenizar_linha("(9.0 3.0 /)")
        valores = [t.valor for t in tokens]
        self.assertEqual(valores, ["(", "9.0", "3.0", "/", ")"])

    def test_operador_divisao_inteira(self):
        tokens = tokenizar_linha("(10 3 //)")
        valores = [t.valor for t in tokens]
        self.assertEqual(valores, ["(", "10", "3", "//", ")"])

    def test_operador_modulo(self):
        tokens = tokenizar_linha("(10 3 %)")
        valores = [t.valor for t in tokens]
        self.assertEqual(valores, ["(", "10", "3", "%", ")"])

    def test_operador_potencia(self):
        tokens = tokenizar_linha("(2 5 ^)")
        valores = [t.valor for t in tokens]
        self.assertEqual(valores, ["(", "2", "5", "^", ")"])

    def test_expressao_aninhada(self):
        tokens = tokenizar_linha("((3.0 2.0 +) (4.0 1.0 -) *)")
        valores = [t.valor for t in tokens]
        self.assertEqual(valores, ["(", "(", "3.0", "2.0", "+", ")", "(", "4.0", "1.0", "-", ")", "*", ")"])

    def test_expressao_aninhada_tripla(self):
        tokens = tokenizar_linha("(((1 2 +) 3 *) 4 /)")
        valores = [t.valor for t in tokens]
        self.assertEqual(valores, ["(", "(", "(", "1", "2", "+", ")", "3", "*", ")", "4", "/", ")"])

    def test_leitura_memoria(self):
        tokens = tokenizar_linha("(MEM)")
        valores = [t.valor for t in tokens]
        self.assertEqual(valores, ["(", "MEM", ")"])
        self.assertEqual(tokens[1].tipo, TIPO_IDENT)

    def test_escrita_memoria(self):
        tokens = tokenizar_linha("(12.5 VARA)")
        self.assertEqual(tokens[1].tipo, TIPO_NUMERO)
        self.assertEqual(tokens[2].tipo, TIPO_IDENT)
        self.assertEqual(tokens[2].valor, "VARA")

    def test_keyword_res_tipo_correto(self):
        tokens = tokenizar_linha("(1 RES)")
        self.assertEqual(tokens[2].tipo, TIPO_KEYWORD)
        self.assertEqual(tokens[2].valor, "RES")

    def test_numero_inteiro(self):
        tokens = tokenizar_linha("(42 7 //)")
        self.assertEqual(tokens[1].tipo, TIPO_NUMERO)
        self.assertEqual(tokens[1].valor, "42")

    def test_numero_real_grande(self):
        tokens = tokenizar_linha("(123456.789 1.0 +)")
        self.assertEqual(tokens[1].valor, "123456.789")

    def test_tipos_tokens_operadores(self):
        for op in ["+", "-", "*", "%", "^"]:
            tokens = tokenizar_linha(f"(1 2 {op})")
            self.assertEqual(tokens[3].tipo, TIPO_OPERADOR)
            self.assertEqual(tokens[3].valor, op)

    def test_tipo_token_divisao_inteira(self):
        tokens = tokenizar_linha("(1 2 //)")
        self.assertEqual(tokens[3].tipo, TIPO_OPERADOR)
        self.assertEqual(tokens[3].valor, "//")

    def test_tipos_parenteses(self):
        tokens = tokenizar_linha("(1 2 +)")
        self.assertEqual(tokens[0].tipo, TIPO_ABRE)
        self.assertEqual(tokens[4].tipo, TIPO_FECHA)


    def test_erro_operador_invalido(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(3.14 2.0 &)")

    def test_erro_numero_malformado(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(3.14.5 2.0 +)")

    def test_erro_virgula_decimal(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(3,45 2.0 +)")

    def test_erro_parenteses_desbalanceados_falta_fechar(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(3.14 2.0 +")

    def test_erro_parenteses_desbalanceados_falta_abrir(self):
        with self.assertRaises(Erros):
            tokenizar_linha("3.14 2.0 +)")

    def test_erro_ponto_final_numero(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(3. 2.0 +)")

    def test_erro_caractere_especial(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(3.0 2.0 @)")

    def test_erro_letra_minuscula(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(3.0 abc +)")

    def test_erro_letra_minuscula_mensagem(self):
        with self.assertRaises(Erros) as ctx:
            tokenizar_linha("(3.0 abc +)")
        self.assertIn("maiúsculas", str(ctx.exception))

    def test_erro_numero_seguido_de_letra(self):
        with self.assertRaises(Erros) as ctx:
            tokenizar_linha("(3.14abc 2.0 +)")
        self.assertIn("malformado", str(ctx.exception))

    def test_erro_numero_inteiro_seguido_de_letra(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(10x 2 +)")

    def test_erro_ponto_sem_digito_antes(self):
        with self.assertRaises(Erros) as ctx:
            tokenizar_linha("(.5 2.0 +)")
        self.assertIn("ponto sem dígito", str(ctx.exception))

    def test_erro_multiplos_pontos(self):
        with self.assertRaises(Erros) as ctx:
            tokenizar_linha("(3.14.5 2.0 +)")
        self.assertIn("múltiplos pontos", str(ctx.exception))

    def test_erro_identificador_com_digito(self):
        with self.assertRaises(Erros) as ctx:
            tokenizar_linha("(10.5 MEM1)")
        self.assertIn("dígito", str(ctx.exception))

    def test_erro_identificador_minuscula_misturada(self):
        with self.assertRaises(Erros) as ctx:
            tokenizar_linha("(10.5 Mem)")
        self.assertIn("minúscula", str(ctx.exception))

    def test_erro_numero_decimal_seguido_letra(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(2.0a 3 +)")

    def test_erro_multiplos_parenteses_faltando(self):
        with self.assertRaises(Erros):
            tokenizar_linha("((3 2 +)")

    def test_erro_parentese_extra_fechando(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(3 2 +))")

    def test_erro_caractere_exclamacao(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(3 2 !)")

    def test_erro_caractere_arroba(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(3 2 @)")

    def test_erro_caractere_cifrão(self):
        with self.assertRaises(Erros):
            tokenizar_linha("(3 2 $)")


if __name__ == "__main__":
    unittest.main()
