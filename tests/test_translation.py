from pathlib import Path
import unittest
from unittest.mock import patch
from app.content import translate_subtitles, translate_lecture_notes


class TranslationTests(unittest.TestCase):
    def test_italian_line_numbers_are_not_subtitle_text(self):
        for answer in ('1 La conoscenza nasce dall’esperienza.', '1\tLa conoscenza nasce dall’esperienza.', '1. La conoscenza nasce dall’esperienza.'):
            with self.subTest(answer=answer), patch('app.content.model_response', return_value=answer):
                self.assertEqual(translate_subtitles([{'text':'Knowledge comes from experience.'}], 'it', Path('bin'), Path('model')), ['La conoscenza nasce dall’esperienza.'])

    def test_empty_translation_fails_without_recursive_retries(self):
        with patch('app.content.model_response', return_value='') as response:
            with self.assertRaises(ValueError):
                translate_subtitles([{'text':'Hello.'}], 'it', Path('bin'), Path('model'))
            self.assertEqual(response.call_count, 1)

    def test_missing_row_is_retried_individually(self):
        with patch('app.content.model_response', side_effect=['1 Primo.', '1 Secondo.']):
            self.assertEqual(translate_subtitles([{'text':'First.'},{'text':'Second.'}], 'it', Path('bin'), Path('model')), ['Primo.','Secondo.'])

    def test_chinese_note_labels_are_localized_without_model_calls(self):
        summary='主题: 原文主题\n要点:\n• 原文观点\n结论: 原文结论'
        with patch('app.content.translate_subtitles', return_value=['Тема лекции','Главная мысль','Вывод лекции']) as translate:
            translated, _, _ = translate_lecture_notes(summary, [], [], 'ru', Path('bin'), Path('model'))
        self.assertEqual(translated, 'Тема: Тема лекции\nОсновные тезисы:\n• Главная мысль\nИтог: Вывод лекции')
        self.assertNotIn('要点:', [row['text'] for row in translate.call_args.args[0]])


if __name__ == '__main__':
    unittest.main()
