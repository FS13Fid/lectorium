import os
import sys
import tempfile
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
from app.speech import SpeechRecognizer, cpu_threads


class SpeechRoutingTests(unittest.TestCase):
    def test_cpu_limit_never_exceeds_available_cores(self):
        with patch.dict(os.environ, {'ASR_CPU_THREADS': '99'}), patch('app.speech.os.sched_getaffinity', return_value={0, 1, 2}, create=True):
            self.assertEqual(cpu_threads(), 3)

    def test_russian_switch_frees_whisper_and_loads_gigaam(self):
        onnx = MagicMock()
        ort = MagicMock()
        options = MagicMock()
        ort.SessionOptions.return_value = options
        vad_options = MagicMock()
        vad_options.return_value.as_kwargs.return_value = {'speech_pad_ms': 100}
        with patch.dict(sys.modules, {'onnx_asr': onnx, 'onnxruntime': ort, 'stt_ru': MagicMock(), 'stt_ru.vad': SimpleNamespace(VadOptions=vad_options)}):
            recognizer = SpeechRecognizer('gigaam-v3-e2e-rnnt', 'base')
            previous = MagicMock()
            recognizer.model, recognizer.engine = previous, 'whisper'
            recognizer.load('ru')
            self.assertEqual(recognizer.engine, 'gigaam')
            self.assertIsNot(recognizer.model, previous)
            self.assertEqual(onnx.load_model.call_args.args[0], 'gigaam-v3-e2e-rnnt')
            self.assertEqual(onnx.load_model.call_args.kwargs['quantization'], 'int8')
            recognizer.transcribe(np.zeros((16000, 1), dtype='float32'), 16000, 'ru')
            self.assertEqual(recognizer.model.recognize.call_args.kwargs['sample_rate'], 16000)

    def test_english_and_italian_use_multilingual_whisper(self):
        for language in ('en', 'it', 'de', 'es', 'zh', 'fr'):
            with self.subTest(language=language), patch.dict(sys.modules, {'faster_whisper': MagicMock()}) as modules:
                model = modules['faster_whisper'].WhisperModel.return_value
                model.transcribe.return_value = (iter([SimpleNamespace(text='test', start=0, end=1)]), None)
                recognizer = SpeechRecognizer('gigaam', 'base')
                self.assertTrue(list(recognizer.transcribe(np.zeros(16000, dtype='float32'), 16000, language)))
                self.assertEqual(recognizer.engine, 'whisper')
                self.assertEqual(model.transcribe.call_args.kwargs['language'], language)
                # Music-backed speech must survive the existing no-VAD path.
                self.assertFalse(model.transcribe.call_args.kwargs['vad_filter'])
                self.assertEqual(model.transcribe.call_args.kwargs['beam_size'], 5)

    def test_detection_does_not_decode_a_transcript(self):
        with tempfile.NamedTemporaryFile(suffix='.wav') as audio:
            with wave.open(audio.name, 'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
                wav.writeframes((np.ones(16000, dtype='<i2') * 1000).tobytes())
            model = MagicMock()
            def no_decoding():
                raise AssertionError('detection must not consume transcription generator')
                yield
            model.transcribe.return_value = (no_decoding(), SimpleNamespace(language='ru'))
            recognizer = SpeechRecognizer('gigaam', 'base')
            recognizer.engine, recognizer.model = 'whisper', model
            self.assertEqual(recognizer.detect_language(audio.name), 'ru')
            self.assertIsNone(model.transcribe.call_args.kwargs['language'])


if __name__ == '__main__':
    unittest.main()
