import unittest
from app.retrieval import terms, variants, lexical_score

class RetrievalTests(unittest.TestCase):
    def test_six_languages(self):
        for text in ['пространство время','space time','Raum Zeit','espacio tiempo','spazio tempo','空间时间']:
            with self.subTest(text=text):
                self.assertEqual(lexical_score(terms(text),terms(text)),1)
    def test_typo_and_transliteration(self):
        corpus=terms('Философия пространство и время')
        for query in ['filosofiya','филосфия','prostranstvo','пространтсво']:
            with self.subTest(query=query):
                self.assertGreater(lexical_score(terms(query),corpus),.65)
                self.assertTrue(any(terms(v)&corpus for v in variants(query,corpus)))
    def test_keyboard_and_accents(self):
        self.assertIn('философия', variants('abkjcjabz',terms('философия')))
        self.assertEqual(lexical_score(terms('razon'),terms('razón')),1)
    def test_unrelated_and_chinese(self):
        self.assertEqual(lexical_score(terms('бананы'),terms('философия')),0)
        self.assertGreater(lexical_score(terms('空间'),terms('空间和时间')),0)
