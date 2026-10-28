"""CPU speech engines: GigaAM for Russian, multilingual Whisper for other languages."""
from __future__ import annotations

import gc
import os
import wave

import numpy as np


def cpu_threads() -> int:
    available = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 2)
    return max(1, min(available, int(os.getenv("ASR_CPU_THREADS", str(min(4, available))))))


class SpeechRecognizer:
    def __init__(self, russian_model: str, multilingual_model: str):
        self.russian_model = russian_model
        self.multilingual_model = multilingual_model
        self.model = None
        self.engine = None

    def release(self):
        self.model = None
        self.engine = None
        gc.collect()

    def load(self, language: str):
        engine = "gigaam" if language == "ru" else "whisper"
        if self.engine == engine:
            return
        # Do not hold both large models in memory on a small VPS.
        self.release()
        if engine == "gigaam":
            import onnx_asr
            import onnxruntime as ort
            from stt_ru.vad import VadOptions

            options = ort.SessionOptions()
            options.intra_op_num_threads = cpu_threads()
            options.inter_op_num_threads = 1
            options.log_severity_level = 3
            options.add_session_config_entry("session.intra_op.allow_spinning", "0")
            options.add_session_config_entry("session.inter_op.allow_spinning", "0")
            config = {"sess_options": options, "providers": ["CPUExecutionProvider"]}
            vad = onnx_asr.load_vad("silero", **config)
            self.model = onnx_asr.load_model(self.russian_model, quantization="int8", **config).with_vad(
                vad, **VadOptions(min_silence_duration_ms=300, speech_pad_ms=100).as_kwargs()
            )
        else:
            try:
                from faster_whisper import WhisperModel
            except ImportError as error:
                raise RuntimeError("На сервере не установлена модель для других языков. Требуется зависимость faster-whisper из requirements.txt.") from error
            self.model = WhisperModel(self.multilingual_model, device="cpu", compute_type="int8",
                                      cpu_threads=cpu_threads(), num_workers=1)
        self.engine = engine

    def detect_language(self, audio_path) -> str:
        self.load("auto")
        # Detection uses voiced audio rather than a silent intro. No transcript is decoded here.
        with wave.open(str(audio_path), "rb") as wav:
            rate = wav.getframerate()
            if rate != 16000 or wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                raise ValueError("Для определения языка нужен моно WAV 16 кГц / 16 бит")
            sample = np.frombuffer(wav.readframes(rate * 120), dtype="<i2").astype(np.float32) / 32768.0
        if not sample.size or float(np.max(np.abs(sample))) < 0.001:
            raise RuntimeError("В начале видео не найдена речь. Выберите язык вручную.")
        _, info = self.model.transcribe(sample, language=None, beam_size=1, vad_filter=True,
                                       condition_on_previous_text=False, language_detection_segments=3,
                                       language_detection_threshold=0.8)
        return (info.language or "").lower()

    def transcribe(self, samples, rate: int, language: str):
        self.load(language)
        mono = np.asarray(samples, dtype=np.float32).reshape(-1)
        if language == "ru":
            return self.model.recognize(mono, sample_rate=rate)
        # Keep sung and music-backed words: the VAD used to drop quiet syllables and
        # whole days from children's songs. The multilingual int8 model and a wider beam
        # improve recognition without requiring a GPU.
        segments, _ = self.model.transcribe(mono, language=language, beam_size=5, vad_filter=False,
                                           condition_on_previous_text=False)
        return segments
