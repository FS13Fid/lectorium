# © 2026 Синакаев Фидель, Мучкаев Марк, Бутров Трофим, Борисов Никита, Попов Роман. Все права защищены. Исходный код: просмотр жюри для оценки; иное использование — по письменному разрешению правообладателей. Полные условия: LICENSE.
from __future__ import annotations

import json
import base64
import asyncio
import datetime
import hashlib
import hmac
import ipaddress
import math
import gc
import os
import re
import secrets
import sys
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid
import socket
import urllib.request
import urllib.error
import wave
from urllib.parse import parse_qs, parse_qsl, urlencode, unquote, urlparse
from collections import Counter
from contextlib import closing
from pathlib import Path

import numpy as np
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.background import BackgroundTask
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv("DATA_DIR", ROOT / "data"))
UPLOADS = Path(os.getenv("UPLOAD_DIR", ROOT / "uploads"))
DATA.mkdir(parents=True, exist_ok=True)
UPLOADS.mkdir(parents=True, exist_ok=True)
WORK = DATA / "working"
WORK.mkdir(parents=True, exist_ok=True)
for private_dir in (DATA, UPLOADS, WORK):
    private_dir.chmod(0o700)
for stale_path in WORK.iterdir():
    shutil.rmtree(stale_path, ignore_errors=True) if stale_path.is_dir() else stale_path.unlink(missing_ok=True)
DB = DATA / "lectures.sqlite3"
KEY_FILE = Path(os.getenv("STORAGE_KEY_FILE", DATA / "storage.key"))
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
EMBEDDING_CACHE = Path(os.getenv("FASTEMBED_CACHE_PATH", DATA / "fastembed_cache"))
ASR_MODEL = os.getenv("ASR_MODEL", "gigaam-v3-e2e-rnnt")
MULTILINGUAL_ASR_MODEL = os.getenv("MULTILINGUAL_ASR_MODEL", "Systran/faster-whisper-base")
SPEECH_LANGUAGES = {"auto": "Автоопределение", "ru": "Русский", "en": "English", "zh": "中文", "de": "Deutsch", "es": "Español"}
SUBTITLE_LANGUAGES = {"ru": "Русский", "en": "English", "zh": "中文", "de": "Deutsch", "es": "Español"}
os.environ.setdefault("HF_HOME", str(DATA / "hf_cache"))

app = FastAPI(title="Лекторий — семантический поиск по лекциям", version="1.0.0")

MEDIA_MAGIC = b"LCTR1"
TEXT_PREFIX = "enc1:"
QUALITY_LEVELS = {"best", "2160", "1440", "1080", "720", "480", "360"}
_video_extractors = None
_storage_key = None
_auth_attempts: dict[str, list[float]] = {}
_auth_attempts_lock = threading.Lock()


def storage_key() -> bytes:
    global _storage_key
    if _storage_key is None:
        try:
            fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "wb") as key_file:
                key_file.write(secrets.token_bytes(32))
                key_file.flush()
                os.fsync(key_file.fileno())
        _storage_key = KEY_FILE.read_bytes()
        if len(_storage_key) != 32:
            raise RuntimeError("Ключ шифрования хранилища повреждён")
    return _storage_key


def encrypt_text(value: str | None) -> str | None:
    if value is None or value.startswith(TEXT_PREFIX):
        return value
    nonce = secrets.token_bytes(12)
    cipher = Cipher(algorithms.AES(storage_key()), modes.GCM(nonce)).encryptor()
    cipher.authenticate_additional_data(b"lectorium-text-v1")
    encrypted = cipher.update(value.encode("utf-8")) + cipher.finalize() + cipher.tag
    return TEXT_PREFIX + base64.urlsafe_b64encode(nonce + encrypted).decode("ascii")


def decrypt_text(value: str | None) -> str | None:
    if value is None or not value.startswith(TEXT_PREFIX):
        return value
    payload = base64.urlsafe_b64decode(value[len(TEXT_PREFIX):].encode("ascii"))
    nonce, encrypted = payload[:12], payload[12:]
    cipher = Cipher(algorithms.AES(storage_key()), modes.GCM(nonce, encrypted[-16:])).decryptor()
    cipher.authenticate_additional_data(b"lectorium-text-v1")
    return (cipher.update(encrypted[:-16]) + cipher.finalize()).decode("utf-8")


def encrypt_blob(value: bytes | None) -> bytes | None:
    if value is None or value.startswith(b"ENC1:"):
        return value
    nonce = secrets.token_bytes(12)
    cipher = Cipher(algorithms.AES(storage_key()), modes.GCM(nonce)).encryptor()
    cipher.authenticate_additional_data(b"lectorium-blob-v1")
    return b"ENC1:" + nonce + cipher.update(value) + cipher.finalize() + cipher.tag


def decrypt_blob(value: bytes | None) -> bytes | None:
    if value is None or not value.startswith(b"ENC1:"):
        return value
    payload = value[5:]
    cipher = Cipher(algorithms.AES(storage_key()), modes.GCM(payload[:12], payload[-16:])).decryptor()
    cipher.authenticate_additional_data(b"lectorium-blob-v1")
    return cipher.update(payload[12:-16]) + cipher.finalize()


def encrypt_media(source: Path, target: Path):
    nonce = secrets.token_bytes(12)
    encryptor = Cipher(algorithms.AES(storage_key()), modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(b"lectorium-media-v1")
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, target.open("wb") as dst:
        dst.write(MEDIA_MAGIC + nonce)
        while chunk := src.read(1024 * 1024):
            dst.write(encryptor.update(chunk))
        dst.write(encryptor.finalize())
        dst.write(encryptor.tag)
        dst.flush()
        os.fsync(dst.fileno())
    target.chmod(0o600)


def decrypt_media(source: Path, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with source.open("rb") as src:
            header = src.read(len(MEDIA_MAGIC) + 12)
            if len(header) != len(MEDIA_MAGIC) + 12 or not header.startswith(MEDIA_MAGIC):
                raise ValueError("Зашифрованное видео имеет неверный формат")
            src.seek(0, os.SEEK_END)
            file_size = src.tell()
            if file_size < len(header) + 16:
                raise ValueError("Зашифрованное видео повреждено")
            src.seek(-16, os.SEEK_END)
            tag = src.read(16)
            cipher = Cipher(algorithms.AES(storage_key()), modes.GCM(header[len(MEDIA_MAGIC):], tag)).decryptor()
            cipher.authenticate_additional_data(b"lectorium-media-v1")
            src.seek(len(header))
            remaining = file_size - len(header) - 16
            with target.open("wb") as dst:
                while remaining:
                    chunk = src.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("Зашифрованное видео обрезано")
                    remaining -= len(chunk)
                    dst.write(cipher.update(chunk))
                dst.write(cipher.finalize())
        target.chmod(0o600)
    except Exception:
        target.unlink(missing_ok=True)
        raise


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.urlsafe_b64encode(salt + digest).decode("ascii")


def password_matches(password: str, encoded: str) -> bool:
    try:
        algorithm, payload = encoded.split("$", 1)
        data = base64.urlsafe_b64decode(payload.encode("ascii"))
        return algorithm == "scrypt" and hmac.compare_digest(password_hash(password, data[:16]).split("$", 1)[1], payload)
    except Exception:
        return False


def enforce_auth_limit(request: Request):
    now = time.time()
    host = request.client.host if request.client else "unknown"
    with _auth_attempts_lock:
        attempts = [stamp for stamp in _auth_attempts.get(host, []) if now - stamp < 900]
        if len(attempts) >= 12:
            _auth_attempts[host] = attempts
            raise HTTPException(429, "Слишком много попыток. Подождите 15 минут и попробуйте снова.", headers={"Retry-After": "900"})
        attempts.append(now)
        _auth_attempts[host] = attempts


def make_session(user_id: str) -> str:
    expires = str(int(time.time()) + 30 * 24 * 60 * 60)
    payload = base64.urlsafe_b64encode(f"{user_id}.{expires}".encode()).decode().rstrip("=")
    signature = hmac.new(storage_key(), payload.encode(), hashlib.sha256).hexdigest()
    return payload + "." + signature


def session_user(token: str | None) -> str | None:
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(storage_key(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode()
        user_id, expires = raw.rsplit(".", 1)
        if int(expires) < int(time.time()):
            return None
        return user_id
    except Exception:
        return None


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        public_paths = {"/", "/api/health", "/api/auth/session", "/api/auth/login", "/api/auth/register"}
        if path in public_paths or path.startswith("/static/") or path.startswith("/api/oauth/"):
            return await call_next(request)
        user_id = session_user(request.cookies.get("lectorium_session"))
        if not user_id:
            return JSONResponse({"detail": "Требуется войти в личный кабинет"}, status_code=401)
        with closing(db()) as con:
            user = con.execute("SELECT blocked FROM users WHERE id=?", (user_id,)).fetchone()
            if not user or user["blocked"]:
                return JSONResponse({"detail": "Учётная запись больше не активна"}, status_code=401)
        request.state.user_id = user_id
        return await call_next(request)

app.add_middleware(SessionMiddleware)
app.mount("/static", StaticFiles(directory=str(ROOT / "app" / "static")), name="static")

_embedder = None
_model_lock = threading.Lock()
_processing_lock = threading.Lock()
_job_registry_lock = threading.Lock()
_job_cancel_events: dict[str, threading.Event] = {}
_job_processes: dict[str, subprocess.Popen] = {}
_vpn_lock = threading.Lock()
_vpn_process: subprocess.Popen | None = None


def db():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA secure_delete=ON")
    return conn


with closing(db()) as con:
    con.executescript("""
      CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, username TEXT NOT NULL COLLATE NOCASE UNIQUE,
        password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user', blocked INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
      );
      CREATE TABLE IF NOT EXISTS oauth_links (
        id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        provider TEXT NOT NULL, subject TEXT NOT NULL, display_name TEXT NOT NULL DEFAULT '',
        email_enc TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(provider,subject), UNIQUE(user_id,provider)
      );
      CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY, value TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS oauth_states (
        state_hash TEXT PRIMARY KEY, provider TEXT NOT NULL, user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        purpose TEXT NOT NULL, expires_at REAL NOT NULL
      );
      CREATE TABLE IF NOT EXISTS lectures (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, source TEXT NOT NULL,
        media_path TEXT, duration REAL DEFAULT 0, status TEXT NOT NULL DEFAULT 'queued',
        error TEXT, summary TEXT DEFAULT '', outline TEXT DEFAULT '[]',
        keywords TEXT DEFAULT '[]', owner_id TEXT REFERENCES users(id), media_type TEXT DEFAULT 'video/mp4',
        quality TEXT NOT NULL DEFAULT 'best', folder_id TEXT REFERENCES folders(id) ON DELETE SET NULL,
        speech_language TEXT NOT NULL DEFAULT 'ru',
        progress INTEGER NOT NULL DEFAULT 0,
        stage TEXT NOT NULL DEFAULT 'В очереди', started_at REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
      );
      CREATE TABLE IF NOT EXISTS folders (
        id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(owner_id,name)
      );
      CREATE TABLE IF NOT EXISTS segments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, lecture_id TEXT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
        start REAL NOT NULL, end REAL NOT NULL, text TEXT NOT NULL, embedding BLOB
      );
      CREATE INDEX IF NOT EXISTS idx_segments_lecture ON segments(lecture_id, start);
    """)

    lecture_columns = {row[1] for row in con.execute("PRAGMA table_info(lectures)")}
    user_columns = {row[1] for row in con.execute("PRAGMA table_info(users)")}
    if "role" not in user_columns:
        con.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
    if "blocked" not in user_columns:
        con.execute("ALTER TABLE users ADD COLUMN blocked INTEGER NOT NULL DEFAULT 0")
    if "owner_id" not in lecture_columns:
        con.execute("ALTER TABLE lectures ADD COLUMN owner_id TEXT REFERENCES users(id)")
    if "media_type" not in lecture_columns:
        con.execute("ALTER TABLE lectures ADD COLUMN media_type TEXT DEFAULT 'video/mp4'")
    if "quality" not in lecture_columns:
        con.execute("ALTER TABLE lectures ADD COLUMN quality TEXT NOT NULL DEFAULT 'best'")
    if "progress" not in lecture_columns:
        con.execute("ALTER TABLE lectures ADD COLUMN progress INTEGER NOT NULL DEFAULT 0")
    if "stage" not in lecture_columns:
        con.execute("ALTER TABLE lectures ADD COLUMN stage TEXT NOT NULL DEFAULT 'В очереди'")
    if "started_at" not in lecture_columns:
        con.execute("ALTER TABLE lectures ADD COLUMN started_at REAL")
    if "eta_seconds" not in lecture_columns:
        con.execute("ALTER TABLE lectures ADD COLUMN eta_seconds INTEGER")
    if "speed" not in lecture_columns:
        con.execute("ALTER TABLE lectures ADD COLUMN speed TEXT")
    if "folder_id" not in lecture_columns:
        con.execute("ALTER TABLE lectures ADD COLUMN folder_id TEXT REFERENCES folders(id) ON DELETE SET NULL")
    if "speech_language" not in lecture_columns:
        con.execute("ALTER TABLE lectures ADD COLUMN speech_language TEXT NOT NULL DEFAULT 'ru'")
    con.execute("UPDATE lectures SET status='queued', progress=0, stage='В очереди' WHERE status='processing'")
    con.execute("UPDATE lectures SET progress=100,stage='Готово',eta_seconds=0,speed=NULL WHERE status='ready'")
    con.execute("UPDATE lectures SET stage='Ошибка обработки',eta_seconds=0,speed=NULL WHERE status='error'")
    bootstrap_user = os.getenv("APP_USER", "lecturer").strip() or "lecturer"
    bootstrap_password = os.getenv("APP_PASSWORD", "")
    bootstrap = con.execute("SELECT id FROM users WHERE username=?", (bootstrap_user,)).fetchone()
    if not bootstrap and bootstrap_password:
        bootstrap_id = str(uuid.uuid4())
        con.execute("INSERT INTO users(id,username,password_hash) VALUES(?,?,?)", (bootstrap_id, bootstrap_user, password_hash(bootstrap_password)))
        bootstrap = {"id": bootstrap_id}
    if bootstrap:
        con.execute("UPDATE lectures SET owner_id=? WHERE owner_id IS NULL", (bootstrap["id"],))
    admin_user = os.getenv("ADMIN_USER", "fidel").strip()
    if admin_user:
        con.execute("UPDATE users SET role='admin' WHERE username=?", (admin_user,))

    # Encrypt legacy plaintext lecture fields and transcript data in place.
    legacy_lecture_rows = con.execute("SELECT id,title,source,error,summary,outline,keywords FROM lectures").fetchall()
    legacy_segment_rows = con.execute("SELECT id,text,embedding FROM segments").fetchall()
    needs_vacuum = any(value is not None and not value.startswith(TEXT_PREFIX) for row in legacy_lecture_rows for value in (row["title"], row["source"], row["error"], row["summary"], row["outline"], row["keywords"]))
    needs_vacuum = needs_vacuum or any((row["text"] is not None and not row["text"].startswith(TEXT_PREFIX)) or (row["embedding"] is not None and not row["embedding"].startswith(b"ENC1:")) for row in legacy_segment_rows)
    for row in legacy_lecture_rows:
        encrypted = tuple(encrypt_text(row[key]) for key in ("title", "source", "error", "summary", "outline", "keywords"))
        con.execute("UPDATE lectures SET title=?,source=?,error=?,summary=?,outline=?,keywords=? WHERE id=?", (*encrypted, row["id"]))
    for row in legacy_segment_rows:
        con.execute("UPDATE segments SET text=?,embedding=? WHERE id=?", (encrypt_text(row["text"]), encrypt_blob(row["embedding"]), row["id"]))
    con.commit()
    if needs_vacuum:
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        con.execute("VACUUM")

storage_key()

# Encrypt old uploaded media after recording each encrypted replacement.
with closing(db()) as con:
    for row in con.execute("SELECT id,media_path FROM lectures WHERE media_path IS NOT NULL").fetchall():
        old_path = Path(row["media_path"])
        if not old_path.exists():
            continue
        if old_path.suffix == ".enc":
            continue
        new_path = UPLOADS / f"{row['id']}.enc"
        if not new_path.exists():
            temp_path = new_path.with_suffix(".enc.tmp")
            encrypt_media(old_path, temp_path)
            temp_path.replace(new_path)
        con.execute("UPDATE lectures SET media_path=? WHERE id=?", (str(new_path), row["id"]))
        media_type = "video/webm" if old_path.suffix.lower() == ".webm" else "video/mp4"
        con.execute("UPDATE lectures SET media_type=? WHERE id=?", (media_type, row["id"]))
        con.commit()
        if old_path != new_path:
            old_path.unlink(missing_ok=True)

# Older releases kept temporary plaintext audio and downloads in per-lecture folders.
for old_work in UPLOADS.iterdir():
    if old_work.is_dir():
        shutil.rmtree(old_work, ignore_errors=True)
    elif old_work.is_file() and old_work.suffix != ".enc":
        replacement = old_work.with_name(old_work.name + ".enc")
        encrypt_media(old_work, replacement)
        old_work.unlink(missing_ok=True)


def embedder():
    global _embedder
    if _embedder is None:
        with _model_lock:
            if _embedder is None:
                from fastembed import TextEmbedding
                _embedder = TextEmbedding(model_name=MODEL_NAME, cache_dir=str(EMBEDDING_CACHE))
    return _embedder


def encode_texts(texts: list[str]) -> np.ndarray:
    vectors = np.asarray(list(embedder().embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.maximum(norms, 1e-12)


def audio_chunks(path: Path, max_seconds: int = 300):
    """Read bounded mono WAV chunks, placing cuts at nearby quiet audio."""
    with wave.open(str(path), "rb") as wav:
        rate = wav.getframerate()
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("Для распознавания нужен моно WAV 16 бит")
        total = wav.getnframes()
        start = 0
        while start < total:
            end = min(total, start + max_seconds * rate)
            if end < total:
                search_start = max(start + rate, end - 8 * rate)
                search_end = min(total, end + 8 * rate)
                wav.setpos(search_start)
                nearby = np.frombuffer(wav.readframes(search_end - search_start), dtype="<i2")
                window = max(1, rate // 4)
                count = len(nearby) // window
                if count:
                    energy = np.abs(nearby[:count * window].astype(np.float32)).reshape(count, window).mean(axis=1)
                    end = search_start + int(np.argmin(energy)) * window
            wav.setpos(start)
            samples = np.frombuffer(wav.readframes(end - start), dtype="<i2").astype(np.float32) / 32768.0
            yield start / rate, end / rate, samples.reshape(-1, 1), rate
            start = end


def set_status(lecture_id: str, status: str, error: str | None = None):
    with closing(db()) as con:
        stage = "Готово" if status == "ready" else "Отменено" if status == "cancelled" else "Ошибка обработки" if status == "error" else "В очереди"
        progress = 100 if status == "ready" else None
        if progress is None:
            con.execute("UPDATE lectures SET status=?, error=?, stage=?, eta_seconds=0, speed=NULL WHERE id=?", (status, encrypt_text(error), stage, lecture_id))
        else:
            con.execute("UPDATE lectures SET status=?, error=?, stage=?, progress=?, eta_seconds=0, speed=NULL WHERE id=?", (status, encrypt_text(error), stage, progress, lecture_id))
        con.commit()


def set_progress(lecture_id: str, progress: int, stage: str, status: str | None = None, eta_seconds: int | None = None, speed: str | None = None):
    progress = max(0, min(100, int(progress)))
    now = time.time()
    with closing(db()) as con:
        if status:
            con.execute("UPDATE lectures SET status=?,progress=?,stage=?,started_at=COALESCE(started_at,?),eta_seconds=?,speed=? WHERE id=?", (status, progress, stage, now, eta_seconds, speed, lecture_id))
        else:
            con.execute("UPDATE lectures SET status=CASE WHEN status='queued' THEN 'processing' ELSE status END,progress=?,stage=?,started_at=COALESCE(started_at,?),eta_seconds=?,speed=? WHERE id=?", (progress, stage, now, eta_seconds, speed, lecture_id))
        con.commit()


def allowed_video_host(host: str) -> bool:
    host = host.lower().rstrip(".")
    allowed = ("youtube.com", "youtu.be", "youtube-nocookie.com", "vimeo.com", "vk.com", "vk.ru", "vkvideo.ru", "vkontakte.ru", "rutube.ru")
    return any(host == domain or host.endswith("." + domain) for domain in allowed)


def supported_video_url(url: str) -> bool:
    global _video_extractors
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        return False
    try:
        if not ipaddress.ip_address(host).is_global:
            return False
    except ValueError:
        pass
    if allowed_video_host(host):
        return True
    try:
        if _video_extractors is None:
            from yt_dlp.extractor import gen_extractors
            _video_extractors = tuple(gen_extractors())
        return any(ie.ie_key() != "Generic" and ie.suitable(url) for ie in _video_extractors)
    except Exception:
        return False


def format_selector(quality: str) -> str:
    if quality == "best":
        return "bv*+ba/b"
    if quality not in QUALITY_LEVELS:
        raise ValueError("Выберите допустимое качество видео")
    return f"bestvideo*[height<={quality}]+bestaudio/best[height<={quality}]"


def safe_title(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value[:120] or "Новая лекция"


def unique_lecture_title(con, owner_id: str, value: str) -> str:
    base = safe_title(value)
    existing = {decrypt_text(row[0]).casefold() for row in con.execute("SELECT title FROM lectures WHERE owner_id=?", (owner_id,)).fetchall()}
    if base.casefold() not in existing:
        return base
    suffix = 2
    while True:
        candidate = safe_title(f"{base[:110]} ({suffix})")
        if candidate.casefold() not in existing:
            return candidate
        suffix += 1


def media_duration(path: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, timeout=30)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def summarize_and_outline(segments: list[dict], language: str = "ru") -> tuple[str, list[dict], list[str]]:
    from app.content import summarize_and_outline as build_notes
    binary = Path(os.getenv("SUMMARY_BINARY", ROOT / "bin" / "llama-cli"))
    model = Path(os.getenv("SUMMARY_MODEL_FILE", DATA / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"))
    return build_notes(segments, binary, model, language=language)


def normalize_video_url(value: str) -> str:
    value = value.strip()
    if not re.match(r"^https?://", value, flags=re.I):
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme == "http":
        parsed = parsed._replace(scheme="https")
        value = parsed.geturl()
    if not supported_video_url(value):
        raise HTTPException(400, "Сайт не распознан как видеоплатформа yt-dlp или ссылка некорректна")
    return value


class JobCancelled(Exception):
    pass


def cancel_running_job(lecture_id: str):
    with _job_registry_lock:
        event = _job_cancel_events.get(lecture_id)
        process = _job_processes.get(lecture_id)
        if event:
            event.set()
        if process and process.poll() is None:
            process.terminate()


def process_lecture(lecture_id: str, source_file: Path | str, is_link: bool = False, quality: str = "best"):
    cancelled = threading.Event()
    with _job_registry_lock:
        _job_cancel_events[lecture_id] = cancelled
    # Keep heavy model work sequential on the small VPS, while queued jobs remain visible.
    try:
        with _processing_lock:
            if cancelled.is_set():
                raise JobCancelled()
            with closing(db()) as con:
                row = con.execute("SELECT status,speech_language FROM lectures WHERE id=?", (lecture_id,)).fetchone()
            if not row or row["status"] == "cancelled":
                raise JobCancelled()
            set_progress(lecture_id, 2, "Подготавливаем задачу", status="processing")
            _process_lecture_job(lecture_id, source_file, is_link, quality, cancelled, row["speech_language"] or "ru")
    except JobCancelled:
        set_status(lecture_id, "cancelled")
    finally:
        with _job_registry_lock:
            _job_cancel_events.pop(lecture_id, None)
            _job_processes.pop(lecture_id, None)


def parse_download_line(line: str) -> tuple[float | None, str | None, str | None, int | None, str | None]:
    match = re.search(
        r"\[download\]\s+([\d\.]+)%"
        r"(?:\s+of\s+~?\s*([\d\.]+\s*[A-Za-z]+))?"
        r"(?:\s+(?:in\s+\S+\s+)?at\s+([\d\.]+\s*[A-Za-z]+/s))?"
        r"(?:\s+ETA\s+(\S+))?",
        line,
    )
    if not match:
        return None, None, None, None, None

    try:
        pct = float(match.group(1))
    except (ValueError, TypeError):
        return None, None, None, None, None

    size_raw = match.group(2)
    speed_raw = match.group(3)
    eta_raw = match.group(4)

    speed_ru = None
    if speed_raw:
        speed_ru = (
            speed_raw.replace("KiB/s", " КБ/с")
            .replace("MiB/s", " МБ/с")
            .replace("GiB/s", " ГБ/с")
            .replace("B/s", " Б/с")
            .strip()
        )

    total_ru = None
    downloaded_ru = None
    if size_raw:
        total_ru = (
            size_raw.replace("KiB", " КБ")
            .replace("MiB", " МБ")
            .replace("GiB", " ГБ")
            .replace("B", " Б")
            .replace("~", "")
            .strip()
        )
        size_match = re.search(r"([\d\.]+)\s*([A-Za-z]+)", size_raw)
        if size_match:
            try:
                tot_val = float(size_match.group(1))
                unit = size_match.group(2)
                dl_val = tot_val * (pct / 100.0)
                unit_ru = (
                    unit.replace("KiB", "КБ")
                    .replace("MiB", "МБ")
                    .replace("GiB", "ГБ")
                    .replace("B", "Б")
                )
                downloaded_ru = f"{dl_val:.1f} {unit_ru}"
            except Exception:
                pass

    eta_sec = None
    if eta_raw and eta_raw != "Unknown":
        try:
            parts = [int(p) for p in eta_raw.split(":")]
            if len(parts) == 3:
                eta_sec = parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2:
                eta_sec = parts[0] * 60 + parts[1]
            elif len(parts) == 1:
                eta_sec = parts[0]
        except Exception:
            pass

    return pct, speed_ru, total_ru, eta_sec, downloaded_ru


def _process_lecture_job(lecture_id: str, source_file: Path | str, is_link: bool = False, quality: str = "best", cancelled: threading.Event | None = None, speech_language: str = "ru"):
    work = WORK / lecture_id
    work.mkdir(parents=True, exist_ok=True)
    local_media = None if is_link else Path(source_file)
    try:
        if cancelled and cancelled.is_set():
            raise JobCancelled()
        if is_link:
            host = (urlparse(str(source_file)).hostname or "").lower()
            if not supported_video_url(str(source_file)):
                raise ValueError("Сайт не распознан как видеоплатформа yt-dlp или ссылка некорректна")
            url = str(source_file)
            target = work / "video.%(ext)s"
            command = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--js-runtimes", "node", "--socket-timeout", "30", "--retries", "2", "--fragment-retries", "2", "-f", format_selector(quality), "--merge-output-format", "mp4"]
            youtube_host = host == "youtu.be" or host.endswith(".youtu.be") or host == "youtube.com" or host.endswith(".youtube.com")
            proxy = (read_setting("youtube.proxy_url") or os.getenv("YTDLP_PROXY", "")).strip()
            if proxy and youtube_host:
                command.extend(["--proxy", proxy])
            command.extend(["--newline", "--progress", "--no-color"])
            command.extend(["-o", str(target), url])
            set_progress(lecture_id, 5, "Подключаемся к сайту")
            output_tail = []
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
            with _job_registry_lock:
                _job_processes[lecture_id] = process
            last_download_pct = -1
            last_download_update = 0.0
            if process.stdout:
                for line in process.stdout:
                    output_tail.append(line.rstrip())
                    if len(output_tail) > 40:
                        output_tail.pop(0)
                    pct_val, speed_ru, total_ru, eta_sec, downloaded_ru = parse_download_line(line)
                    if pct_val is not None:
                        overall_pct = min(39, 7 + int(pct_val * 0.32))
                        now = time.time()
                        if now - last_download_update >= 0.7 or int(pct_val) != last_download_pct:
                            pct_label = f"{int(pct_val)}%" if pct_val >= 10 else f"{pct_val:.1f}%"
                            if speed_ru and downloaded_ru and total_ru:
                                stage = f"Скачиваем видео · {pct_label} · {speed_ru} ({downloaded_ru} из {total_ru})"
                            elif speed_ru:
                                stage = f"Скачиваем видео · {pct_label} · {speed_ru}"
                            else:
                                stage = f"Скачиваем видео · {pct_label}"
                            set_progress(lecture_id, overall_pct, stage, eta_seconds=eta_sec, speed=speed_ru)
                            last_download_update = now
                            last_download_pct = int(pct_val)
            if cancelled and cancelled.is_set() and process.poll() is None:
                process.terminate()
            return_code = process.wait(timeout=7200)
            with _job_registry_lock:
                _job_processes.pop(lecture_id, None)
            if cancelled and cancelled.is_set():
                raise JobCancelled()
            downloaded = next((p for p in work.glob("video.*") if p.is_file() and p.suffix not in {".part", ".ytdl"}), None)
            if return_code != 0 or not downloaded:
                detail = "\n".join(output_tail)[-800:]
                if not detail:
                    detail = "Источник не отдал видео. Проверьте, что ролик публичный и доступен для просмотра."
                raise RuntimeError(detail)
            set_progress(lecture_id, 40, "Видео скачано · готовим аудио", eta_seconds=10)
            encrypted_path = UPLOADS / f"{lecture_id}.enc"
            encrypt_media(downloaded, encrypted_path)
            # Keep the already-downloaded working copy for audio extraction; avoid a full decrypt-and-copy pass.
            local_media = downloaded
            media_type = "video/webm" if downloaded.suffix.lower() == ".webm" else "video/mp4"
            with closing(db()) as con:
                con.execute("UPDATE lectures SET media_path=?,media_type=? WHERE id=?", (str(encrypted_path), media_type, lecture_id)); con.commit()
        elif source_file.suffix == ".enc":
            local_media = work / "source.mp4"
            decrypt_media(source_file, local_media)
        if not local_media or not local_media.exists():
            raise RuntimeError("Не удалось скачать видео по ссылке")
        if cancelled and cancelled.is_set():
            raise JobCancelled()
        set_progress(lecture_id, 43, "Извлекаем звуковую дорожку", eta_seconds=8)
        audio = work / "audio.wav"
        ffmpeg = subprocess.Popen(["ffmpeg", "-y", "-i", str(local_media), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with _job_registry_lock:
            _job_processes[lecture_id] = ffmpeg
        ffmpeg_out, ffmpeg_err = ffmpeg.communicate(timeout=7200)
        with _job_registry_lock:
            _job_processes.pop(lecture_id, None)
        if cancelled and cancelled.is_set():
            raise JobCancelled()
        if ffmpeg.returncode:
            raise subprocess.CalledProcessError(ffmpeg.returncode, "ffmpeg", output=ffmpeg_out, stderr=ffmpeg_err)
        duration = media_duration(local_media)
        speech_name = SPEECH_LANGUAGES.get(speech_language, SPEECH_LANGUAGES["ru"])
        requested_language = speech_language
        detected_language = None if requested_language == "auto" else requested_language
        model = None
        if speech_language == "ru":
            set_progress(lecture_id, 47, "Загружаем GigaAM для русской речи")
            from stt_ru import Transcriber
            from stt_ru.audio import Audio
            from stt_ru.vad import VadOptions
            model = Transcriber(model=ASR_MODEL, quantization="int8", split_channels=False,
                                vad=VadOptions(min_silence_duration_ms=300, speech_pad_ms=100))
        else:
            set_progress(lecture_id, 47, f"Загружаем мультиязычную модель речи · {speech_name}")
            from faster_whisper import WhisperModel
            model = WhisperModel(MULTILINGUAL_ASR_MODEL, device="cpu", compute_type="int8",
                                 cpu_threads=max(1, int(os.getenv("ASR_CPU_THREADS", "2"))), num_workers=1)
        set_progress(lecture_id, 50, f"Распознаём речь · {speech_name}")
        transcript = []
        transcribe_start = time.time()
        for offset, chunk_end, samples, rate in audio_chunks(audio):
            if cancelled and cancelled.is_set():
                raise JobCancelled()
            if speech_language == "ru":
                result = model.transcribe_audio(Audio(samples, rate))
                recognized = result.segments
            else:
                recognized, info = model.transcribe(samples.reshape(-1), language=None if detected_language is None else detected_language,
                    beam_size=5, vad_filter=False, condition_on_previous_text=False)
                if requested_language == "auto" and detected_language is None:
                    candidate = (getattr(info, "language", None) or "").lower()
                    if candidate not in {"ru", "en", "zh", "de", "es"}:
                        raise RuntimeError("Автоопределение выявило неподдерживаемый язык. Выберите русский, английский, китайский, немецкий или испанский вручную.")
                    detected_language = candidate
                    speech_language = candidate
                    speech_name = SPEECH_LANGUAGES[candidate]
                    with closing(db()) as con:
                        con.execute("UPDATE lectures SET speech_language=? WHERE id=?", (candidate, lecture_id)); con.commit()
                    if candidate == "ru":
                        recognized = []
                        del model
                        from stt_ru import Transcriber
                        from stt_ru.audio import Audio
                        from stt_ru.vad import VadOptions
                        model = Transcriber(model=ASR_MODEL, quantization="int8", split_channels=False,
                                            vad=VadOptions(min_silence_duration_ms=300, speech_pad_ms=100))
                        recognized = model.transcribe_audio(Audio(samples, rate)).segments
                    else:
                        recognized = list(recognized)
            for segment in recognized:
                text = re.sub(r"\s+", " ", segment.text).strip()
                if text:
                    start = max(0.0, offset + float(segment.start))
                    transcript.append({"start": start, "end": max(start + .2, offset + float(segment.end)), "text": text})
            elapsed = max(.5, time.time() - transcribe_start)
            audio_done = min(duration, chunk_end)
            audio_pct = min(100, int(audio_done / max(1, duration) * 100))
            rate_ratio = audio_done / elapsed
            eta = max(1, int(max(0, duration - audio_done) / max(.1, rate_ratio)))
            stage = f"Распознаём речь · {speech_name} · {audio_pct}% ({int(audio_done // 60)} из {int(duration // 60)} мин.)"
            set_progress(lecture_id, min(78, 50 + int(audio_pct * .28)), stage,
                         eta_seconds=eta, speed=f"{rate_ratio:.1f}x аудио")
        del model
        gc.collect()
        if not transcript:
            raise RuntimeError("В аудио не удалось распознать речь")
        set_progress(lecture_id, 80, "Составляем пересказ, тезисы и заголовки")
        summary, outline, keywords = summarize_and_outline(transcript, language=speech_language)
        set_progress(lecture_id, 89, "Загружаем модель смыслового поиска", eta_seconds=8)
        vectors = []
        batch_size = 32
        total_batches = max(1, math.ceil(len(transcript) / batch_size))
        for batch_idx, offset in enumerate(range(0, len(transcript), batch_size)):
            if cancelled and cancelled.is_set():
                raise JobCancelled()
            chunk = encode_texts([s["text"] for s in transcript[offset:offset + batch_size]])
            vectors.extend(chunk)
            pct = 89 + int((batch_idx + 1) / total_batches * 8)
            rem_chunks = total_batches - (batch_idx + 1)
            eta = max(1, int(rem_chunks * 0.7) + 4)
            set_progress(lecture_id, pct, f"Создаём смысловой индекс · {batch_idx + 1} из {total_batches}", eta_seconds=eta)
        set_progress(lecture_id, 98, "Сохраняем лекцию", eta_seconds=1)
        with closing(db()) as con:
            con.execute("DELETE FROM segments WHERE lecture_id=?", (lecture_id,))
            con.executemany("INSERT INTO segments(lecture_id,start,end,text,embedding) VALUES(?,?,?,?,?)", [(lecture_id, s["start"], s["end"], encrypt_text(s["text"]), encrypt_blob(np.asarray(v, dtype=np.float32).tobytes())) for s, v in zip(transcript, vectors)])
            con.execute("UPDATE lectures SET status='ready', progress=100, stage='Готово', eta_seconds=0, speed=NULL, duration=?, summary=?, outline=?, keywords=?, error=NULL WHERE id=?", (duration, encrypt_text(summary), encrypt_text(json.dumps(outline, ensure_ascii=False)), encrypt_text(json.dumps(keywords, ensure_ascii=False)), lecture_id))
            con.commit()
    except JobCancelled:
        set_status(lecture_id, "cancelled")
    except Exception as exc:
        message = str(exc)
        if isinstance(exc, subprocess.CalledProcessError):
            message = (exc.stderr or b"").decode(errors="replace")[-800:] or "Ошибка обработки медиа"
            failed_host = (urlparse(str(source_file)).hostname or "").lower() if is_link else ""
            failed_youtube = failed_host == "youtu.be" or failed_host.endswith(".youtu.be") or failed_host == "youtube.com" or failed_host.endswith(".youtube.com")
            if failed_youtube and not os.getenv("YTDLP_PROXY"):
                message += "\nПрямое соединение VPS с YouTube недоступно. Задайте внешний HTTP/SOCKS5-прокси через YTDLP_PROXY."
        set_status(lecture_id, "error", message[-1000:])
    finally:
        shutil.rmtree(work, ignore_errors=True)


def lecture_dict(row):
    d = dict(row)
    d["title"] = decrypt_text(d.get("title"))
    d["source"] = decrypt_text(d.get("source"))
    d["error"] = decrypt_text(d.get("error"))
    d["summary"] = decrypt_text(d.get("summary"))
    d["outline"] = json.loads(decrypt_text(d.get("outline")) or "[]")
    d["keywords"] = json.loads(decrypt_text(d.get("keywords")) or "[]")
    d.pop("owner_id", None)
    d["video_url"] = f"/media/{d['id']}" if d.get("media_path") and Path(d["media_path"]).exists() else None
    if d.get("started_at") is not None:
        try:
            d["started_at"] = float(d["started_at"])
        except (ValueError, TypeError):
            pass
    elif d.get("created_at"):
        try:
            dt = datetime.datetime.fromisoformat(str(d["created_at"]).replace(" ", "T") + "+00:00")
            d["started_at"] = dt.timestamp()
        except Exception:
            d["started_at"] = time.time()
    return d


class Credentials(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


def account_row(user_id: str):
    with closing(db()) as con:
        return con.execute("SELECT id,username,role,created_at FROM users WHERE id=? AND blocked=0", (user_id,)).fetchone()


def require_admin(request: Request):
    with closing(db()) as con:
        row = con.execute("SELECT role FROM users WHERE id=?", (request.state.user_id,)).fetchone()
    if not row or row["role"] != "admin":
        raise HTTPException(403, "Доступ только для администратора")


def read_setting(key: str, default: str = "") -> str:
    with closing(db()) as con:
        row = con.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return decrypt_text(row[0]) if row else default


def write_setting(key: str, value: str):
    with closing(db()) as con:
        con.execute("INSERT INTO app_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, encrypt_text(value)))
        con.commit()


def delete_setting(key: str):
    with closing(db()) as con:
        con.execute("DELETE FROM app_settings WHERE key=?", (key,))
        con.commit()


class SettingsPayload(BaseModel):
    values: dict[str, str | bool]


ADMIN_SETTING_KEYS = {
    *(f"oauth.{provider}.{suffix}" for provider in ("yandex", "github", "mailru") for suffix in ("client_id", "client_secret")),
    "youtube.proxy_url", "vpn.subscription_url", "vpn.selected_node",
}
ADMIN_SECRET_KEYS = {key for key in ADMIN_SETTING_KEYS if key.endswith("client_secret") or key == "vpn.subscription_url"}


@app.get("/api/admin/settings")
def admin_settings(request: Request):
    require_admin(request)
    result = {}
    for key in ADMIN_SETTING_KEYS:
        value = read_setting(key)
        result[key] = {"configured": bool(value)} if key in ADMIN_SECRET_KEYS else value
    result["callbacks"] = {provider: f"https://demoground.ru/api/oauth/{provider}/callback" for provider in ("yandex", "github", "mailru")}
    return result


@app.put("/api/admin/settings")
def save_admin_settings(body: SettingsPayload, request: Request):
    require_admin(request)
    for key, value in body.values.items():
        if key not in ADMIN_SETTING_KEYS:
            raise HTTPException(400, "Неизвестный параметр")
        normalized = str(value).strip()
        if key == "vpn.subscription_url" and normalized:
            parsed = urlparse(normalized)
            if parsed.scheme not in {"https", "http"} or not parsed.netloc:
                raise HTTPException(400, "Ссылка подписки должна начинаться с https://")
        if key in ADMIN_SECRET_KEYS and not normalized:
            continue
        write_setting(key, normalized)
    return {"ok": True}


class ProxyTestPayload(BaseModel):
    proxy_url: str = ""


@app.post("/api/admin/proxy/test")
def admin_test_proxy(body: ProxyTestPayload, request: Request):
    require_admin(request)
    proxy = body.proxy_url.strip() or read_setting("youtube.proxy_url") or os.getenv("YTDLP_PROXY", "").strip()
    if not proxy:
        raise HTTPException(400, "Укажите адрес прокси для проверки")
    t0 = time.time()
    try:
        cmd = ["curl", "-s", "-I", "--proxy", proxy, "--max-time", "8", "https://www.youtube.com/generate_204"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode != 0 or ("204" not in res.stdout and "200" not in res.stdout):
            error_msg = res.stderr.strip() or res.stdout.strip() or f"Код возврата {res.returncode}"
            return {"ok": False, "message": f"YouTube не ответил через прокси: {error_msg[:120]}"}
        latency_ms = int((time.time() - t0) * 1000)
        return {"ok": True, "latency_ms": latency_ms, "message": f"YouTube доступен! Задержка: {latency_ms} мс"}
    except Exception as e:
        return {"ok": False, "message": f"Ошибка соединения: {str(e)[:120]}"}


def parse_vless_link(raw: str, index: int) -> dict:
    parsed = urlparse(raw.strip())
    if parsed.scheme.lower() != "vless" or not parsed.hostname or not parsed.port or not parsed.username:
        raise ValueError("Некорректный VLESS URI")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    label = unquote(parsed.fragment).strip() or f"Сервер {index + 1}"
    outbound = {"type": "vless", "tag": f"node-{index}", "server": parsed.hostname, "server_port": parsed.port, "uuid": unquote(parsed.username)}
    if query.get("flow"):
        outbound["flow"] = query["flow"]
    security = query.get("security", "none").lower()
    if security in {"tls", "reality"}:
        tls = {"enabled": True, "server_name": query.get("sni", ""), "insecure": query.get("allowInsecure", "0") in {"1", "true"}}
        if query.get("alpn"):
            tls["alpn"] = query["alpn"].split(",")
        if query.get("fp"):
            tls["utls"] = {"enabled": True, "fingerprint": query["fp"]}
        if security == "reality":
            tls["reality"] = {"enabled": True, "public_key": query.get("pbk", ""), "short_id": query.get("sid", "")}
        outbound["tls"] = tls
    transport = query.get("type", "tcp").lower()
    if transport == "ws":
        ws = {"type": "ws", "path": query.get("path", "/")}
        host = query.get("host")
        if host:
            ws["headers"] = {"Host": host}
        outbound["transport"] = ws
    elif transport == "grpc":
        outbound["transport"] = {"type": "grpc", "service_name": query.get("serviceName", "")}
    elif transport in {"http", "h2"}:
        outbound["transport"] = {"type": "http", "host": [query.get("host", parsed.hostname)], "path": query.get("path", "/")}
    elif transport not in {"tcp", "raw"}:
        raise ValueError("Этот VLESS-транспорт пока не поддерживается")
    if security == "reality" and (not query.get("pbk") or not query.get("sni")):
        raise ValueError("В узле Reality не хватает SNI или public key")
    return {"name": label[:100], "outbound": outbound}


def fetch_vpn_nodes() -> list[dict]:
    url = read_setting("vpn.subscription_url")
    if not url:
        raise HTTPException(400, "Сначала сохраните ссылку VPN-подписки")

    hwid = read_setting("vpn.device_hwid")
    if not hwid:
        hwid = "12345678-1234-1234-1234-123456789abc"
        write_setting("vpn.device_hwid", hwid)

    info = {}
    try:
        req_meta = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )
        with urllib.request.urlopen(req_meta, timeout=8) as r:
            html = r.read().decode("utf-8", errors="replace")
            if 'data-panel="' in html:
                b64_panel = html.split('data-panel="')[1].split('"')[0]
                panel = json.loads(base64.b64decode(b64_panel).decode("utf-8"))
                user = panel.get("response", {}).get("user", {})
                info = {
                    "username": user.get("username", ""),
                    "trafficUsed": user.get("trafficUsed", ""),
                    "trafficLimit": user.get("trafficLimit", ""),
                    "expiresAt": user.get("expiresAt", ""),
                    "daysLeft": user.get("daysLeft", ""),
                    "isActive": user.get("isActive", True)
                }
    except Exception:
        pass
    if info:
        write_setting("vpn.subscription_info", json.dumps(info, ensure_ascii=False))

    nodes = []

    try:
        req_happ = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Happ/3.6.0",
                "X-HWID": hwid,
                "HWID": hwid,
                "Accept": "application/json, text/plain, */*"
            }
        )
        with urllib.request.urlopen(req_happ, timeout=18) as resp:
            raw = resp.read().decode("utf-8-sig", errors="replace").strip()
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    for idx, item in enumerate(data):
                        rem = (item.get("remarks") or f"Сервер {idx+1}").strip()
                        obs = item.get("outbounds", [])
                        if not obs:
                            continue
                        rem_lower = rem.lower()
                        if any(bad in rem_lower for bad in ["включите hwid", "не поддерживается", "все инструкции", "не помогло?", "удалите лишние устройства"]):
                            continue
                        main_ob = obs[0]
                        proto = main_ob.get("protocol", "vless")
                        nodes.append({
                            "name": rem,
                            "type": "xray",
                            "protocol": proto,
                            "outbound": main_ob
                        })
            except Exception:
                pass
    except Exception:
        pass

    if not nodes:
        content = ""
        try:
            req_plain = urllib.request.Request(
                url,
                headers={"User-Agent": "Happ/1.0", "X-HWID": hwid, "Accept": "text/plain,*/*"}
            )
            with urllib.request.urlopen(req_plain, timeout=20) as resp:
                content = resp.read(2_000_000).decode("utf-8-sig", errors="replace").strip()
        except Exception:
            raise HTTPException(502, "Не удалось получить VPN-подписку. Проверьте адрес и доступность сервиса.")
        if "\n" not in content and not re.match(r"^[a-z][a-z0-9+.-]*://", content, re.I):
            try:
                decoded = base64.b64decode(content + "=" * (-len(content) % 4)).decode("utf-8", errors="replace").strip()
                if re.search(r"(?m)^(?:vless|vmess|trojan|ss|socks)://", decoded, re.I):
                    content = decoded
            except Exception:
                pass
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if not line.lower().startswith("vless://"):
                continue
            try:
                node = parse_vless_link(line, len(nodes))
                if re.match(r"^(включите|или приложение|все инструкции|не помогло\?|удалите лишние устройства)", node["name"].strip(), re.I):
                    continue
                node["type"] = "sing-box"
                node["protocol"] = "vless"
                nodes.append(node)
            except Exception:
                continue

    if nodes:
        write_setting("vpn.nodes", json.dumps(nodes, ensure_ascii=False))
        selected = read_setting("vpn.selected_node", "")
        if not selected or not selected.isdigit() or int(selected) >= len(nodes):
            best_idx = 0
            for i, n in enumerate(nodes):
                if "youtube" in n["name"].lower():
                    best_idx = i
                    break
            write_setting("vpn.selected_node", str(best_idx))

    return nodes


@app.get("/api/admin/vpn/nodes")
def admin_vpn_nodes(request: Request):
    require_admin(request)
    nodes = fetch_vpn_nodes()
    write_setting("vpn.nodes", json.dumps(nodes, ensure_ascii=False))
    selected = read_setting("vpn.selected_node", "0")
    info = {}
    try:
        info = json.loads(read_setting("vpn.subscription_info", "{}"))
    except Exception:
        pass
    message = f"Найдено серверов: {len(nodes)}" if nodes else "В подписке не найдено рабочих VLESS-узлов. Проверьте ссылку."
    return {
        "nodes": [{"index": i, "name": node["name"], "protocol": node.get("protocol", "vless")} for i, node in enumerate(nodes)],
        "selected": selected,
        "message": message,
        "info": info
    }


@app.get("/api/admin/vpn/current")
def admin_vpn_current(request: Request):
    require_admin(request)
    nodes_text = read_setting("vpn.nodes", "[]")
    try:
        nodes = json.loads(nodes_text)
    except Exception:
        nodes = []
    selected = read_setting("vpn.selected_node", "0")
    info = {}
    try:
        info = json.loads(read_setting("vpn.subscription_info", "{}"))
    except Exception:
        pass
    return {
        "nodes": [{"index": i, "name": node["name"], "protocol": node.get("protocol", "vless")} for i, node in enumerate(nodes)],
        "selected": selected,
        "message": f"Загружено серверов: {len(nodes)}" if nodes else "",
        "info": info
    }


class VPNSelection(BaseModel):
    index: int


@app.post("/api/admin/vpn/select")
def admin_select_vpn_node(body: VPNSelection, request: Request):
    require_admin(request)
    try:
        nodes = json.loads(read_setting("vpn.nodes", "[]"))
        node = nodes[body.index]
    except (IndexError, TypeError, json.JSONDecodeError):
        raise HTTPException(400, "Сначала обновите список серверов и выберите узел")
    if not shutil.which("xray") and not shutil.which("sing-box"):
        raise HTTPException(503, "На сервере не установлен Xray или sing-box")
    write_setting("vpn.selected_node", str(body.index))
    stop_vpn_proxy()
    return {"ok": True, "name": node["name"]}


@app.post("/api/admin/vpn/test")
def admin_test_vpn(request: Request):
    require_admin(request)
    stop_vpn_proxy()
    proxy = youtube_proxy_url()
    if not proxy:
        raise HTTPException(400, "VPN-прокси не настроен или список серверов пуст")
    t0 = time.time()
    try:
        cmd = ["curl", "-s", "-I", "--socks5", "127.0.0.1:20801", "--max-time", "6", "https://www.youtube.com/generate_204"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if res.returncode != 0 or ("204" not in res.stdout and "200" not in res.stdout):
            error_msg = res.stderr.strip() or res.stdout.strip() or f"Код ошибки {res.returncode}"
            return {"ok": False, "message": f"YouTube не ответил: {error_msg[:120]}"}
        latency_ms = int((time.time() - t0) * 1000)
        return {"ok": True, "latency_ms": latency_ms, "message": f"YouTube доступен! Задержка: {latency_ms} мс"}
    except Exception as e:
        return {"ok": False, "message": f"Ошибка проверки соединения: {str(e)[:120]}"}


def stop_vpn_proxy():
    global _vpn_process
    with _vpn_lock:
        process, _vpn_process = _vpn_process, None
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except Exception:
                process.kill()


def youtube_proxy_url() -> str | None:
    global _vpn_process
    nodes_text = read_setting("vpn.nodes")
    if not nodes_text:
        if read_setting("vpn.subscription_url"):
            raise RuntimeError("Обновите список VPN-серверов в панели администратора")
        return None
    try:
        nodes = json.loads(nodes_text)
        index = int(read_setting("vpn.selected_node", "0"))
        node = nodes[index]
    except Exception as exc:
        raise RuntimeError("Выбранный VPN-узел больше недоступен. Обновите список серверов.") from exc

    port = 20801
    node_type = node.get("type", "xray")

    with _vpn_lock:
        if _vpn_process and _vpn_process.poll() is None:
            return f"socks5://127.0.0.1:{port}"

        config_path = WORK / "youtube-proxy.json"

        if node_type == "xray" and shutil.which("xray"):
            binary = shutil.which("xray")
            config = {
                "log": {"loglevel": "warning"},
                "inbounds": [{
                    "port": port,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "settings": {"auth": "noauth", "udp": True}
                }],
                "outbounds": [
                    node["outbound"],
                    {"protocol": "freedom", "tag": "direct"}
                ]
            }
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
            config_path.chmod(0o600)
            check = subprocess.run([binary, "run", "-test", "-c", str(config_path)], capture_output=True, text=True, timeout=15)
            if check.returncode:
                raise RuntimeError("Ошибка конфигурации Xray: " + (check.stderr or check.stdout)[-400:])
            _vpn_process = subprocess.Popen([binary, "run", "-c", str(config_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            binary = shutil.which("sing-box")
            if not binary:
                raise RuntimeError("На сервере не найден исполняемый файл proxy (xray / sing-box)")
            config = {
                "log": {"level": "error"},
                "inbounds": [{"type": "mixed", "tag": "local", "listen": "127.0.0.1", "listen_port": port}],
                "outbounds": [node["outbound"], {"type": "direct", "tag": "direct"}],
                "route": {"final": node["outbound"].get("tag", "proxy")}
            }
            config_path.write_text(json.dumps(config), encoding="utf-8")
            config_path.chmod(0o600)
            check = subprocess.run([binary, "check", "-c", str(config_path)], capture_output=True, text=True, timeout=15)
            if check.returncode:
                raise RuntimeError("Не удалось проверить VPN-узел: " + (check.stderr or check.stdout)[-400:])
            _vpn_process = subprocess.Popen([binary, "run", "-c", str(config_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        process = _vpn_process

    deadline = time.time() + 12
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("VPN-узел завершился сразу после запуска")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=.3):
                return f"socks5://127.0.0.1:{port}"
        except OSError:
            time.sleep(.2)
    stop_vpn_proxy()
    raise RuntimeError("Локальный прокси не открыл соединение")


def auth_response(request: Request, user_id: str, username: str):
    user = account_row(user_id)
    response = JSONResponse({"authenticated": True, "user": {"id": user_id, "username": username, "role": user["role"]}})
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"
    response.set_cookie("lectorium_session", make_session(user_id), max_age=30 * 24 * 60 * 60, httponly=True, secure=secure, samesite="lax", path="/")
    return response


@app.get("/api/auth/session")
def auth_session(request: Request):
    user_id = session_user(request.cookies.get("lectorium_session"))
    user = account_row(user_id) if user_id else None
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "user": {"id": user["id"], "username": user["username"], "role": user["role"]}}


@app.post("/api/auth/login")
def login(body: Credentials, request: Request):
    enforce_auth_limit(request)
    username = body.username.strip()
    with closing(db()) as con:
        user = con.execute("SELECT id,username,password_hash,blocked FROM users WHERE username=?", (username,)).fetchone()
    if user and user["blocked"]:
        raise HTTPException(403, "Учётная запись заблокирована. Обратитесь к администратору")
    if not user or not password_matches(body.password, user["password_hash"]):
        raise HTTPException(401, "Неверный логин или пароль")
    return auth_response(request, user["id"], user["username"])


@app.post("/api/auth/register")
def register(body: Credentials, request: Request):
    enforce_auth_limit(request)
    username = body.username.strip().lower()
    password = body.password
    if not re.fullmatch(r"[a-z0-9._-]{3,32}", username):
        raise HTTPException(400, "Логин: 3–32 символа, латинские буквы, цифры, точка, дефис или подчёркивание")
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(400, "Пароль должен содержать от 8 до 128 символов")
    user_id = str(uuid.uuid4())
    try:
        with closing(db()) as con:
            con.execute("INSERT INTO users(id,username,password_hash) VALUES(?,?,?)", (user_id, username, password_hash(password)))
            con.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Такой логин уже занят")
    return auth_response(request, user_id, username)


@app.post("/api/auth/logout")
def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie("lectorium_session", path="/")
    return response


@app.post("/api/auth/password")
def change_password(body: PasswordChange, request: Request):
    user_id = request.state.user_id
    with closing(db()) as con:
        user = con.execute("SELECT password_hash FROM users WHERE id=?", (user_id,)).fetchone()
        if not user or not password_matches(body.current_password, user["password_hash"]):
            raise HTTPException(400, "Текущий пароль введён неверно")
        if len(body.new_password) < 8 or len(body.new_password) > 128:
            raise HTTPException(400, "Новый пароль должен содержать от 8 до 128 символов")
        con.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash(body.new_password), user_id))
        con.commit()
    response = JSONResponse({"ok": True})
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"
    response.set_cookie("lectorium_session", make_session(user_id), max_age=30 * 24 * 60 * 60, httponly=True, secure=secure, samesite="lax", path="/")
    return response


@app.get("/api/account")
def account(request: Request):
    user = account_row(request.state.user_id)
    with closing(db()) as con:
        counts = con.execute("SELECT COUNT(*) AS total, SUM(CASE WHEN status='ready' THEN 1 ELSE 0 END) AS ready FROM lectures WHERE owner_id=?", (request.state.user_id,)).fetchone()
        links = con.execute("SELECT provider,display_name FROM oauth_links WHERE user_id=? ORDER BY provider", (request.state.user_id,)).fetchall()
    available = {provider: bool(read_setting(f"oauth.{provider}.client_id") and
                                (provider == "mailru" or read_setting(f"oauth.{provider}.client_secret")))
                 for provider in ("yandex", "github", "mailru")}
    avatar = read_setting(f"account.avatar.{request.state.user_id}")
    social_avatar = read_setting(f"account.social_avatar.{request.state.user_id}")
    return {"username": user["username"], "created_at": user["created_at"], "lectures": counts["total"], "ready": counts["ready"] or 0, "encrypted": True,
            "avatar": avatar or social_avatar or "",
            "linked_providers": [{"provider": row["provider"], "display_name": row["display_name"]} for row in links],
            "oauth_available": available}


class AccountAvatarPayload(BaseModel):
    avatar: str


@app.put("/api/account/avatar")
def update_account_avatar(payload: AccountAvatarPayload, request: Request):
    value = payload.avatar.strip()
    if value and not re.fullmatch(r"(?:[А-ЯЁA-Z]{1,3}|✦|◉|❋|☼|🌿|📚|✍️|🎓)", value):
        match = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/]+={0,2})", value)
        if not match:
            raise HTTPException(400, "Введите до трёх русских или латинских букв, выберите готовый аватар или загрузите PNG, JPEG либо WebP")
        try:
            image = base64.b64decode(match.group(2), validate=True)
        except Exception as exc:
            raise HTTPException(400, "Не удалось прочитать изображение") from exc
        if len(image) > 2 * 1024 * 1024:
            raise HTTPException(413, "Изображение должно быть не больше 2 МБ")
        signatures = {"png": image.startswith(b"\x89PNG\r\n\x1a\n"), "jpeg": image.startswith(b"\xff\xd8\xff"), "webp": image.startswith(b"RIFF") and image[8:12] == b"WEBP"}
        if not signatures[match.group(1)]:
            raise HTTPException(400, "Формат изображения не совпадает с содержимым файла")
    write_setting(f"account.avatar.{request.state.user_id}", value)
    return {"avatar": value or read_setting(f"account.social_avatar.{request.state.user_id}")}


OAUTH_PROVIDERS = {
    "yandex": {"authorize": "https://oauth.yandex.ru/authorize", "token": "https://oauth.yandex.ru/token", "userinfo": "https://login.yandex.ru/info?format=json", "scope": "login:info"},
    "github": {"authorize": "https://github.com/login/oauth/authorize", "token": "https://github.com/login/oauth/access_token", "userinfo": "https://api.github.com/user", "scope": "read:user"},
    "mailru": {"authorize": "https://id.vk.ru/authorize", "token": "https://id.vk.ru/oauth2/auth", "userinfo": "https://id.vk.ru/oauth2/user_info", "scope": "vkid.personal_info"},
}


def oauth_provider_identity(provider: str, code: str, state: str = "", device_id: str = "") -> tuple[str, str, str, str]:
    cfg = OAUTH_PROVIDERS[provider]
    client_id = read_setting(f"oauth.{provider}.client_id")
    client_secret = read_setting(f"oauth.{provider}.client_secret")
    callback = f"https://demoground.ru/api/oauth/{provider}/callback"
    data = {"client_id": client_id, "client_secret": client_secret, "code": code, "redirect_uri": callback, "grant_type": "authorization_code"}
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    if provider == "mailru":
        if not device_id:
            raise ValueError("VK ID не передал идентификатор устройства")
        verifier_key = f"oauth.vkid.verifier.{hashlib.sha256(state.encode()).hexdigest()}"
        verifier = read_setting(verifier_key)
        delete_setting(verifier_key)
        if not verifier:
            raise ValueError("Истёк код проверки VK ID")
        params = {"grant_type": "authorization_code", "redirect_uri": callback, "client_id": client_id,
                  "code_verifier": verifier, "state": state, "device_id": device_id}
        token_req = urllib.request.Request(cfg["token"] + "?" + urlencode(params), data=urlencode({"code": code}).encode(), headers=headers, method="POST")
    else:
        token_req = urllib.request.Request(cfg["token"], data=urlencode(data).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(token_req, timeout=20) as response:
        token_data = json.loads(response.read())
    access_token = token_data.get("access_token")
    if not access_token:
        raise ValueError("Провайдер не выдал токен авторизации")
    if provider == "mailru":
        if not hmac.compare_digest(str(token_data.get("state", "")), state):
            raise ValueError("VK ID вернул неверное состояние авторизации")
        info_req = urllib.request.Request(cfg["userinfo"] + "?" + urlencode({"client_id": client_id}),
                                          data=urlencode({"access_token": access_token}).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(info_req, timeout=20) as response:
            profile_data = json.loads(response.read())
        profile = profile_data.get("user", profile_data)
        avatar = profile.get("avatar", "")
        if urlparse(avatar).scheme != "https" or urlparse(avatar).hostname != "vk.com" and not (urlparse(avatar).hostname or "").endswith(".userapi.com"):
            avatar = ""
        name = " ".join(part for part in (profile.get("first_name"), profile.get("last_name")) if part).strip() or "VK ID"
        return str(profile.get("user_id") or profile.get("id") or ""), name, "", avatar
    if provider == "yandex":
        info_req = urllib.request.Request(cfg["userinfo"], headers={"Authorization": f"OAuth {access_token}"})
        with urllib.request.urlopen(info_req, timeout=20) as response:
            profile = json.loads(response.read())
        avatar_id = str(profile.get("default_avatar_id") or "")
        avatar = f"https://avatars.yandex.net/get-yapic/{avatar_id}/islands-200" if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", avatar_id) else ""
        return str(profile["id"]), profile.get("login", "Яндекс"), "", avatar
    if provider == "github":
        info_req = urllib.request.Request(cfg["userinfo"], headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Lectorium"})
        with urllib.request.urlopen(info_req, timeout=20) as response:
            profile = json.loads(response.read())
        avatar = profile.get("avatar_url", "")
        if urlparse(avatar).hostname != "avatars.githubusercontent.com" or urlparse(avatar).scheme != "https":
            avatar = ""
        return str(profile["id"]), profile.get("login", "GitHub"), "", avatar
    raise ValueError("Неизвестный OAuth-провайдер")


@app.get("/api/oauth/{provider}/start")
def oauth_start(provider: str, request: Request, link: bool = False):
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(404, "Провайдер не найден")
    client_id = read_setting(f"oauth.{provider}.client_id")
    client_secret = read_setting(f"oauth.{provider}.client_secret")
    if not client_id or (provider != "mailru" and not client_secret):
        raise HTTPException(503, "Провайдер ещё не настроен администратором")
    user_id = session_user(request.cookies.get("lectorium_session")) if link else None
    if link and not user_id:
        raise HTTPException(401, "Войдите в аккаунт, чтобы привязать соцсеть")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64) if provider == "mailru" else ""
    purpose = "link" if link else "login"
    with closing(db()) as con:
        con.execute("INSERT INTO oauth_states(state_hash,provider,user_id,purpose,expires_at) VALUES(?,?,?,?,?)", (hashlib.sha256(state.encode()).hexdigest(), provider, user_id, purpose, time.time() + 600))
        con.commit()
    callback = f"https://demoground.ru/api/oauth/{provider}/callback"
    query = {"client_id": client_id, "redirect_uri": callback, "response_type": "code", "state": state, "scope": OAUTH_PROVIDERS[provider]["scope"]}
    if provider == "mailru":
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        query.update({"code_challenge": challenge, "code_challenge_method": "s256"})
        write_setting(f"oauth.vkid.verifier.{hashlib.sha256(state.encode()).hexdigest()}", verifier)
    if provider == "github":
        query["allow_signup"] = "true"
    response = RedirectResponse(OAUTH_PROVIDERS[provider]["authorize"] + "?" + urlencode(query), status_code=302)
    response.set_cookie("lectorium_oauth_state", state, max_age=600, httponly=True, secure=True, samesite="lax", path="/")
    return response


@app.get("/api/oauth/{provider}/callback")
def oauth_callback(provider: str, request: Request, code: str = "", state: str = "", error: str = "", device_id: str = ""):
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(404, "Провайдер не найден")
    if error or not code or not state or not hmac.compare_digest(state, request.cookies.get("lectorium_oauth_state", "")):
        return RedirectResponse("/?oauth_error=authorization_failed", status_code=303)
    digest = hashlib.sha256(state.encode()).hexdigest()
    with closing(db()) as con:
        state_row = con.execute("SELECT * FROM oauth_states WHERE state_hash=? AND provider=? AND expires_at>?", (digest, provider, time.time())).fetchone()
        con.execute("DELETE FROM oauth_states WHERE state_hash=?", (digest,))
        con.commit()
    if not state_row:
        return RedirectResponse("/?oauth_error=state_expired", status_code=303)
    try:
        subject, display_name, email, avatar_url = oauth_provider_identity(provider, code, state=state, device_id=device_id)
    except Exception:
        return RedirectResponse("/?oauth_error=provider_failed", status_code=303)
    if state_row["purpose"] == "link":
        user_id = state_row["user_id"]
        try:
            with closing(db()) as con:
                con.execute("INSERT INTO oauth_links(id,user_id,provider,subject,display_name,email_enc) VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), user_id, provider, subject, display_name, encrypt_text(email)))
                con.commit()
        except sqlite3.IntegrityError:
            return RedirectResponse("/?oauth_error=already_linked", status_code=303)
        if avatar_url:
            write_setting(f"account.social_avatar.{user_id}", avatar_url)
        response = RedirectResponse("/?linked=" + provider, status_code=303)
    else:
        with closing(db()) as con:
            linked = con.execute("SELECT u.id,u.username FROM oauth_links o JOIN users u ON u.id=o.user_id WHERE o.provider=? AND o.subject=?", (provider, subject)).fetchone()
        if not linked:
            return RedirectResponse("/?oauth_error=not_linked", status_code=303)
        if avatar_url:
            write_setting(f"account.social_avatar.{linked['id']}", avatar_url)
        response = RedirectResponse("/", status_code=303)
        secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"
        response.set_cookie("lectorium_session", make_session(linked["id"]), max_age=30 * 24 * 60 * 60, httponly=True, secure=secure, samesite="lax", path="/")
    response.delete_cookie("lectorium_oauth_state", path="/")
    return response


@app.get("/api/lectures")
def list_lectures(request: Request):
    with closing(db()) as con:
        rows = con.execute("SELECT * FROM lectures WHERE owner_id=? ORDER BY created_at DESC", (request.state.user_id,)).fetchall()
        return [lecture_dict(r) for r in rows]


def resolve_or_create_folder(con, user_id: str, folder_id: str | None = None, new_folder_name: str | None = None) -> str | None:
    target_name = re.sub(r"\s+", " ", new_folder_name or "").strip()
    if target_name:
        if len(target_name) > 50:
            target_name = target_name[:50]
        rows = con.execute("SELECT id, name FROM folders WHERE owner_id=?", (user_id,)).fetchall()
        for r in rows:
            if decrypt_text(r["name"]).casefold() == target_name.casefold():
                return r["id"]
        new_id = str(uuid.uuid4())
        con.execute("INSERT INTO folders(id,owner_id,name) VALUES(?,?,?)", (new_id, user_id, encrypt_text(target_name)))
        return new_id
    if folder_id and folder_id.strip():
        fid = folder_id.strip()
        if con.execute("SELECT 1 FROM folders WHERE id=? AND owner_id=?", (fid, user_id)).fetchone():
            return fid
    return None


@app.post("/api/lectures/upload", status_code=202)
async def upload_lecture(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(""),
    folder_id: str = Form(""),
    new_folder_name: str = Form(""),
    speech_language: str = Form("auto")
):
    if speech_language not in SPEECH_LANGUAGES:
        raise HTTPException(400, "Выберите поддерживаемый язык распознавания")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".mp4", ".webm"}:
        raise HTTPException(400, "Загрузите видео MP4 или WebM")
    lecture_id = str(uuid.uuid4())
    path = UPLOADS / f"{lecture_id}.enc"
    staging = WORK / f"{lecture_id}{ext}.upload"
    size = 0
    try:
        with staging.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 500 * 1024 * 1024:
                    raise HTTPException(413, "Размер файла превышает 500 МБ")
                out.write(chunk)
        encrypt_media(staging, path)
    except Exception:
        staging.unlink(missing_ok=True)
        path.unlink(missing_ok=True)
        raise
    finally:
        staging.unlink(missing_ok=True)
    if await request.is_disconnected():
        path.unlink(missing_ok=True)
        raise HTTPException(499, "Загрузка отменена")
    with closing(db()) as con:
        con.execute("BEGIN IMMEDIATE")
        final_folder_id = resolve_or_create_folder(con, request.state.user_id, folder_id, new_folder_name)
        display_title = unique_lecture_title(con, request.state.user_id, title or Path(file.filename or "upload").stem)
        con.execute("INSERT INTO lectures(id,title,source,media_path,status,owner_id,media_type,folder_id,started_at,speech_language) VALUES(?,?,?,?,?,?,?,?,?,?)", (lecture_id, encrypt_text(display_title), encrypt_text(file.filename or "upload"), str(path), "queued", request.state.user_id, "video/webm" if ext == ".webm" else "video/mp4", final_folder_id, time.time(), speech_language)); con.commit()
    background.add_task(process_lecture, lecture_id, path)
    return {"id": lecture_id, "folder_id": final_folder_id}


class LinkRequest(BaseModel):
    url: str
    title: str = ""
    quality: str = "best"
    folder_id: str | None = None
    new_folder_name: str | None = None
    speech_language: str = "auto"


@app.post("/api/lectures/link", status_code=202)
def add_link(body: LinkRequest, background: BackgroundTasks, request: Request):
    return _add_link(body, background, request.state.user_id)


def _add_link(body: LinkRequest, background: BackgroundTasks, owner_id: str):
    if body.speech_language not in SPEECH_LANGUAGES:
        raise HTTPException(400, "Выберите поддерживаемый язык распознавания")
    url = normalize_video_url(body.url)
    quality = body.quality if body.quality in QUALITY_LEVELS else ""
    if not quality:
        raise HTTPException(400, "Выберите качество из списка")
    lecture_id = str(uuid.uuid4())
    with closing(db()) as con:
        con.execute("BEGIN IMMEDIATE")
        final_folder_id = resolve_or_create_folder(con, owner_id, body.folder_id, body.new_folder_name)
        display_title = unique_lecture_title(con, owner_id, body.title or "Лекция по ссылке")
        con.execute("INSERT INTO lectures(id,title,source,status,owner_id,quality,folder_id,started_at,speech_language) VALUES(?,?,?,?,?,?,?,?,?)", (lecture_id, encrypt_text(display_title), encrypt_text(url), "queued", owner_id, quality, final_folder_id, time.time(), body.speech_language)); con.commit()
    background.add_task(process_lecture, lecture_id, url, True, quality)
    return {"id": lecture_id, "folder_id": final_folder_id}


@app.get("/api/lectures/{lecture_id}")
def get_lecture(lecture_id: str, request: Request):
    with closing(db()) as con:
        row = con.execute("SELECT * FROM lectures WHERE id=? AND owner_id=?", (lecture_id, request.state.user_id)).fetchone()
        if not row: raise HTTPException(404, "Лекция не найдена")
        return lecture_dict(row)


@app.post("/api/lectures/{lecture_id}/retry", status_code=202)
def retry_lecture(lecture_id: str, background: BackgroundTasks, request: Request):
    with closing(db()) as con:
        row = con.execute("SELECT id, source, media_path,quality,status FROM lectures WHERE id=? AND owner_id=?", (lecture_id, request.state.user_id)).fetchone()
    if not row:
        raise HTTPException(404, "Лекция не найдена")
    if row["status"] in {"queued", "processing"}:
        return {"id": lecture_id, "status": row["status"]}
    stored_media = Path(row["media_path"]) if row["media_path"] else None
    if stored_media and stored_media.exists():
        source_file, is_link = stored_media, False
    else:
        original_source = decrypt_text(row["source"])
        source_file = original_source
        is_link = urlparse(original_source).scheme == "https"
        if not is_link or not supported_video_url(original_source):
            raise HTTPException(400, "Исходный файл больше не доступен для повтора")
    with closing(db()) as con:
        con.execute("UPDATE lectures SET status='queued',error=NULL,progress=0,stage='В очереди',started_at=?,eta_seconds=NULL,speed=NULL WHERE id=?", (time.time(), lecture_id))
        con.commit()
    background.add_task(process_lecture, lecture_id, source_file, is_link, row["quality"] or "best")
    return {"id": lecture_id, "status": "queued"}


@app.post("/api/lectures/{lecture_id}/cancel")
def cancel_lecture(lecture_id: str, request: Request):
    with closing(db()) as con:
        row = con.execute("SELECT status FROM lectures WHERE id=? AND owner_id=?", (lecture_id, request.state.user_id)).fetchone()
        if not row:
            raise HTTPException(404, "Лекция не найдена")
        if row["status"] not in {"queued", "processing"}:
            raise HTTPException(409, "Эта обработка уже завершена")
        con.execute("UPDATE lectures SET status='cancelled',error=NULL,stage='Отменено' WHERE id=?", (lecture_id,))
        con.commit()
    cancel_running_job(lecture_id)
    return {"id": lecture_id, "status": "cancelled"}


class FolderRequest(BaseModel):
    name: str


class FolderAssignment(BaseModel):
    folder_id: str | None = None
    new_folder_name: str | None = None


@app.get("/api/folders")
def list_folders(request: Request):
    with closing(db()) as con:
        rows = con.execute("SELECT f.id,f.name,f.created_at,COUNT(l.id) AS lecture_count FROM folders f LEFT JOIN lectures l ON l.folder_id=f.id AND l.owner_id=f.owner_id WHERE f.owner_id=? GROUP BY f.id ORDER BY f.name COLLATE NOCASE", (request.state.user_id,)).fetchall()
    result = [{**dict(row), "name": decrypt_text(row["name"])} for row in rows]
    return sorted(result, key=lambda folder: folder["name"].casefold())


@app.post("/api/folders", status_code=201)
def create_folder(body: FolderRequest, request: Request):
    name = re.sub(r"\s+", " ", body.name).strip()
    if not name or len(name) > 50:
        raise HTTPException(400, "Название папки должно содержать от 1 до 50 символов")
    folder_id = str(uuid.uuid4())
    with closing(db()) as con:
        con.execute("BEGIN IMMEDIATE")
        existing = [decrypt_text(row[0]).casefold() for row in con.execute("SELECT name FROM folders WHERE owner_id=?", (request.state.user_id,)).fetchall()]
        if name.casefold() in existing:
            raise HTTPException(409, "Папка с таким названием уже есть")
        con.execute("INSERT INTO folders(id,owner_id,name) VALUES(?,?,?)", (folder_id, request.state.user_id, encrypt_text(name)))
        con.commit()
    return {"id": folder_id, "name": name, "lecture_count": 0}


@app.delete("/api/folders/{folder_id}")
def delete_folder(folder_id: str, request: Request):
    with closing(db()) as con:
        row = con.execute("SELECT id FROM folders WHERE id=? AND owner_id=?", (folder_id, request.state.user_id)).fetchone()
        if not row:
            raise HTTPException(404, "Папка не найдена")
        con.execute("UPDATE lectures SET folder_id=NULL WHERE folder_id=? AND owner_id=?", (folder_id, request.state.user_id))
        con.execute("DELETE FROM folders WHERE id=?", (folder_id,))
        con.commit()
    return {"ok": True}


@app.patch("/api/lectures/{lecture_id}/folder")
def move_lecture(lecture_id: str, body: FolderAssignment, request: Request):
    with closing(db()) as con:
        con.execute("BEGIN IMMEDIATE")
        owned = con.execute("SELECT id FROM lectures WHERE id=? AND owner_id=?", (lecture_id, request.state.user_id)).fetchone()
        if not owned:
            raise HTTPException(404, "Лекция не найдена")
        final_folder_id = resolve_or_create_folder(con, request.state.user_id, body.folder_id, body.new_folder_name)
        con.execute("UPDATE lectures SET folder_id=? WHERE id=?", (final_folder_id, lecture_id))
        con.commit()
    return {"ok": True, "folder_id": final_folder_id}


@app.get("/api/lectures/{lecture_id}/segments")
def get_segments(lecture_id: str, request: Request):
    with closing(db()) as con:
        owned = con.execute("SELECT 1 FROM lectures WHERE id=? AND owner_id=?", (lecture_id, request.state.user_id)).fetchone()
        if not owned: raise HTTPException(404, "Лекция не найдена")
        rows = con.execute("SELECT id,start,end,text FROM segments WHERE lecture_id=? ORDER BY start", (lecture_id,)).fetchall()
        return [{**dict(r), "text": decrypt_text(r["text"])} for r in rows]


class SubtitleTranslationRequest(BaseModel):
    target_language: str
    offset: int = 0
    limit: int = 12


@app.post("/api/lectures/{lecture_id}/subtitles/translate")
def translate_lecture_subtitles(lecture_id: str, body: SubtitleTranslationRequest, request: Request):
    """Translate a bounded batch in memory; the original transcript and media stay untouched."""
    if body.target_language not in SUBTITLE_LANGUAGES:
        raise HTTPException(400, "Выберите поддерживаемый язык перевода")
    if body.offset < 0 or not 1 <= body.limit <= 12:
        raise HTTPException(400, "Недопустимый диапазон субтитров")
    with closing(db()) as con:
        lecture = con.execute("SELECT status FROM lectures WHERE id=? AND owner_id=?", (lecture_id, request.state.user_id)).fetchone()
        if not lecture:
            raise HTTPException(404, "Лекция не найдена")
        if lecture["status"] != "ready":
            raise HTTPException(409, "Перевод доступен после обработки лекции")
        total = con.execute("SELECT COUNT(*) FROM segments WHERE lecture_id=?", (lecture_id,)).fetchone()[0]
        rows = con.execute("SELECT start,end,text FROM segments WHERE lecture_id=? ORDER BY start LIMIT ? OFFSET ?", (lecture_id, body.limit, body.offset)).fetchall()
    if not rows:
        return {"total": total, "offset": body.offset, "items": []}
    binary = Path(os.getenv("SUMMARY_BINARY", ROOT / "bin" / "llama-cli"))
    model = Path(os.getenv("SUMMARY_MODEL_FILE", DATA / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"))
    if not binary.is_file() or not model.is_file():
        raise HTTPException(503, "Локальная модель перевода временно недоступна")
    from app.content import translate_subtitles
    source = [{"start": row["start"], "end": row["end"], "text": decrypt_text(row["text"])} for row in rows]
    try:
        translated = translate_subtitles(source, body.target_language, binary, model)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Перевод занял слишком много времени. Повторите попытку.")
    except Exception:
        raise HTTPException(502, "Не удалось перевести эту часть лекции. Повторите попытку.")
    if len(translated) != len(source):
        raise HTTPException(502, "Не удалось надёжно разобрать перевод этой части. Повторите попытку.")
    return {"total": total, "offset": body.offset,
            "items": [{"index": body.offset + index, "start": row["start"], "end": row["end"], "text": translated[index]}
                      for index, row in enumerate(rows)]}


@app.post("/api/lectures/{lecture_id}/outline/rebuild")
def rebuild_outline(lecture_id: str, request: Request):
    with closing(db()) as con:
        lecture = con.execute("SELECT status,speech_language FROM lectures WHERE id=? AND owner_id=?", (lecture_id, request.state.user_id)).fetchone()
        if not lecture:
            raise HTTPException(404, "Лекция не найдена")
        if lecture["status"] != "ready":
            raise HTTPException(409, "Оглавление можно обновить после обработки лекции")
        rows = con.execute("SELECT start,end,text FROM segments WHERE lecture_id=? ORDER BY start", (lecture_id,)).fetchall()
    segments = [{"start": row["start"], "end": row["end"], "text": decrypt_text(row["text"])} for row in rows]
    summary, outline, keywords = summarize_and_outline(segments, language=lecture["speech_language"] or "ru")
    with closing(db()) as con:
        con.execute("UPDATE lectures SET summary=?,outline=?,keywords=? WHERE id=? AND owner_id=?", (encrypt_text(summary), encrypt_text(json.dumps(outline, ensure_ascii=False)), encrypt_text(json.dumps(keywords, ensure_ascii=False)), lecture_id, request.state.user_id))
        con.commit()
    return {"summary": summary, "outline": outline, "keywords": keywords}


@app.get("/api/search")
def search(request: Request, q: str, limit: int = 10):
    q = q.strip()
    if len(q) < 2: return []
    with closing(db()) as con:
        rows = con.execute("SELECT s.*, l.title, l.id as lecture_id, l.media_path FROM segments s JOIN lectures l ON l.id=s.lecture_id WHERE l.status='ready' AND l.owner_id=? AND s.embedding IS NOT NULL", (request.state.user_id,)).fetchall()
    if not rows: return []
    query_vec = encode_texts([q])[0]
    stop = {"который", "которая", "которые", "потому", "поэтому", "например", "сейчас", "вообще", "значит", "можно", "будет", "здесь", "также", "когда", "чтобы", "просто", "этого", "этот", "это", "они", "она", "есть", "быть", "как", "что", "или", "для", "при", "над", "под"}
    query_terms = {word.lower() for word in re.findall(r"[А-Яа-яЁёA-Za-z0-9-]{3,}", q) if word.lower() not in stop}
    scores = []
    for row in rows:
        semantic = float(np.dot(query_vec, np.frombuffer(decrypt_blob(row["embedding"]), dtype=np.float32)))
        terms = {word.lower() for word in re.findall(r"[А-Яа-яЁёA-Za-z0-9-]{3,}", decrypt_text(row["text"]))}
        lexical = len(query_terms & terms) / max(1, len(query_terms))
        combined = max(0.0, min(1.0, (semantic + 1) / 2)) * .72 + lexical * .28
        scores.append((combined, row))
    scores.sort(key=lambda item: item[0], reverse=True)
    results = []
    per_lecture = Counter()
    for score, row in scores:
        if per_lecture[row["lecture_id"]] >= 4:
            continue
        if any(r["lecture_id"] == row["lecture_id"] and abs(r["start"] - row["start"]) < 90 for r in results):
            continue
        video_url = f"/media/{Path(row['media_path']).relative_to(UPLOADS).as_posix()}" if row["media_path"] and Path(row["media_path"]).exists() else None
        results.append({"score": round(score, 3), "text": decrypt_text(row["text"]), "start": row["start"], "end": row["end"], "lecture_id": row["lecture_id"], "title": decrypt_text(row["title"]), "video_url": f"/media/{row['lecture_id']}" if video_url else None})
        per_lecture[row["lecture_id"]] += 1
        if len(results) >= max(1, min(limit, 30)):
            break
    return results


@app.delete("/api/lectures/{lecture_id}")
def delete_lecture(lecture_id: str, request: Request):
    cancel_running_job(lecture_id)
    with closing(db()) as con:
        row = con.execute("SELECT media_path FROM lectures WHERE id=? AND owner_id=?", (lecture_id, request.state.user_id)).fetchone()
        if not row: raise HTTPException(404, "Лекция не найдена")
        con.execute("DELETE FROM lectures WHERE id=?", (lecture_id,)); con.commit()
    shutil.rmtree(WORK / lecture_id, ignore_errors=True)
    if row["media_path"]:
        Path(row["media_path"]).unlink(missing_ok=True)
    return {"ok": True}


class RoleChange(BaseModel):
    role: str


class AdminPassword(BaseModel):
    password: str


class AdminUserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class AdminUserEdit(BaseModel):
    username: str


class AdminUserBlock(BaseModel):
    blocked: bool


@app.get("/api/admin/users")
def admin_users(request: Request):
    require_admin(request)
    with closing(db()) as con:
        rows = con.execute("SELECT u.id,u.username,u.role,u.blocked,u.created_at,COUNT(l.id) AS lectures,SUM(CASE WHEN l.status='ready' THEN 1 ELSE 0 END) AS ready FROM users u LEFT JOIN lectures l ON l.owner_id=u.id GROUP BY u.id ORDER BY u.created_at").fetchall()
    return [{**dict(row), "ready": row["ready"] or 0,
             "avatar": read_setting(f"account.avatar.{row['id']}") or read_setting(f"account.social_avatar.{row['id']}")}
            for row in rows]


@app.post("/api/admin/users", status_code=201)
def admin_create_user(body: AdminUserCreate, request: Request):
    require_admin(request)
    username = body.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9._-]{3,32}", username):
        raise HTTPException(400, "Логин: 3–32 символа, латинские буквы, цифры, точка, дефис или подчёркивание")
    if len(body.password) < 8 or len(body.password) > 128:
        raise HTTPException(400, "Пароль должен содержать от 8 до 128 символов")
    if body.role not in {"admin", "user"}:
        raise HTTPException(400, "Недопустимая роль")
    user_id = str(uuid.uuid4())
    try:
        with closing(db()) as con:
            con.execute("INSERT INTO users(id,username,password_hash,role) VALUES(?,?,?,?)", (user_id, username, password_hash(body.password), body.role))
            con.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Такой логин уже занят")
    return {"id": user_id, "username": username, "role": body.role}


@app.patch("/api/admin/users/{user_id}")
def admin_edit_user(user_id: str, body: AdminUserEdit, request: Request):
    require_admin(request)
    username = body.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9._-]{3,32}", username):
        raise HTTPException(400, "Логин: 3–32 символа, латинские буквы, цифры, точка, дефис или подчёркивание")
    try:
        with closing(db()) as con:
            if not con.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
                raise HTTPException(404, "Аккаунт не найден")
            con.execute("UPDATE users SET username=? WHERE id=?", (username, user_id))
            con.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Такой логин уже занят")
    return {"id": user_id, "username": username}


@app.patch("/api/admin/users/{user_id}/blocked")
def admin_set_blocked(user_id: str, body: AdminUserBlock, request: Request):
    require_admin(request)
    with closing(db()) as con:
        target = con.execute("SELECT id,role FROM users WHERE id=?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(404, "Аккаунт не найден")
        if user_id == request.state.user_id and body.blocked:
            raise HTTPException(400, "Нельзя заблокировать текущий аккаунт администратора")
        if body.blocked and target["role"] == "admin" and con.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND blocked=0").fetchone()[0] <= 1:
            raise HTTPException(409, "Нельзя заблокировать последнего активного администратора")
        con.execute("UPDATE users SET blocked=? WHERE id=?", (int(body.blocked), user_id))
        con.commit()
    return {"id": user_id, "blocked": body.blocked}


@app.get("/api/admin/lectures")
def admin_lectures(request: Request):
    require_admin(request)
    with closing(db()) as con:
        rows = con.execute("SELECT l.id,l.title,l.status,l.progress,l.stage,l.created_at,l.media_path,u.id AS owner_id,u.username AS owner FROM lectures l LEFT JOIN users u ON u.id=l.owner_id ORDER BY l.created_at DESC").fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["title"] = decrypt_text(item["title"])
        path = Path(item.pop("media_path")) if item["media_path"] else None
        if path and path.exists():
            item["size_bytes"] = path.stat().st_size
        else:
            work_dir = WORK / item["id"]
            item["size_bytes"] = sum(p.stat().st_size for p in work_dir.rglob("*") if p.is_file()) if work_dir.exists() else 0
        result.append(item)
    return result


@app.patch("/api/admin/users/{user_id}/role")
def admin_set_role(user_id: str, body: RoleChange, request: Request):
    require_admin(request)
    if body.role not in {"admin", "user"}:
        raise HTTPException(400, "Роль должна быть admin или user")
    with closing(db()) as con:
        target = con.execute("SELECT id,role FROM users WHERE id=?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(404, "Аккаунт не найден")
        if user_id == request.state.user_id and body.role == "user":
            raise HTTPException(400, "Нельзя снять роль администратора у текущего аккаунта")
        if target["role"] == "admin" and body.role == "user":
            admins = con.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
            if admins <= 1:
                raise HTTPException(409, "Нельзя снять права с последнего администратора")
        con.execute("UPDATE users SET role=? WHERE id=?", (body.role, user_id))
        con.commit()
    return {"id": user_id, "role": body.role}


@app.post("/api/admin/users/{user_id}/password")
def admin_set_password(user_id: str, body: AdminPassword, request: Request):
    require_admin(request)
    if len(body.password) < 8 or len(body.password) > 128:
        raise HTTPException(400, "Пароль должен содержать от 8 до 128 символов")
    with closing(db()) as con:
        if not con.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
            raise HTTPException(404, "Аккаунт не найден")
        con.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash(body.password), user_id))
        con.commit()
    return {"ok": True}


@app.delete("/api/admin/lectures/{lecture_id}")
def admin_delete_lecture(lecture_id: str, request: Request):
    require_admin(request)
    cancel_running_job(lecture_id)
    with closing(db()) as con:
        row = con.execute("SELECT media_path FROM lectures WHERE id=?", (lecture_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Лекция не найдена")
        con.execute("DELETE FROM lectures WHERE id=?", (lecture_id,))
        con.commit()
    shutil.rmtree(WORK / lecture_id, ignore_errors=True)
    if row["media_path"]:
        Path(row["media_path"]).unlink(missing_ok=True)
    return {"ok": True}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: str, request: Request):
    require_admin(request)
    if user_id == request.state.user_id:
        raise HTTPException(400, "Нельзя удалить текущий аккаунт администратора")
    with closing(db()) as con:
        user = con.execute("SELECT id,role FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(404, "Аккаунт не найден")
        if user["role"] == "admin" and con.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0] <= 1:
            raise HTTPException(409, "Нельзя удалить последнего администратора")
        rows = con.execute("SELECT id,media_path FROM lectures WHERE owner_id=?", (user_id,)).fetchall()
        for row in rows:
            cancel_running_job(row["id"])
            con.execute("DELETE FROM lectures WHERE id=?", (row["id"],))
        con.execute("DELETE FROM folders WHERE owner_id=?", (user_id,))
        con.execute("DELETE FROM users WHERE id=?", (user_id,))
        con.commit()
    for row in rows:
        shutil.rmtree(WORK / row["id"], ignore_errors=True)
        if row["media_path"]:
            Path(row["media_path"]).unlink(missing_ok=True)
    return {"ok": True}


@app.get("/media/{lecture_id}")
def get_media(lecture_id: str, request: Request):
    with closing(db()) as con:
        row = con.execute("SELECT media_path,media_type FROM lectures WHERE id=? AND owner_id=?", (lecture_id, request.state.user_id)).fetchone()
    if not row or not row["media_path"]:
        raise HTTPException(404, "Видео не найдено")
    encrypted_path = Path(row["media_path"])
    if not encrypted_path.exists():
        raise HTTPException(404, "Видео не найдено")
    temporary = WORK / f"stream-{lecture_id}-{secrets.token_hex(6)}.video"
    decrypt_media(encrypted_path, temporary)
    return FileResponse(temporary, media_type=row["media_type"] or "video/mp4", background=BackgroundTask(temporary.unlink, missing_ok=True), headers={"Cache-Control": "private, no-store"})


@app.get("/api/lectures/{lecture_id}/download")
def download_media(lecture_id: str, request: Request):
    with closing(db()) as con:
        row = con.execute("SELECT media_path,media_type,title FROM lectures WHERE id=? AND owner_id=? AND status='ready'", (lecture_id, request.state.user_id)).fetchone()
    if not row or not row["media_path"]:
        raise HTTPException(404, "Видео не найдено")
    encrypted_path = Path(row["media_path"])
    if not encrypted_path.exists():
        raise HTTPException(404, "Видео не найдено")
    ext = ".webm" if row["media_type"] == "video/webm" else ".mp4"
    base = re.sub(r"[^\w\- ]+", "", decrypt_text(row["title"]), flags=re.UNICODE).strip(" ._- ")[:80] or "Лекция"
    temporary = WORK / f"download-{lecture_id}-{secrets.token_hex(6)}{ext}"
    decrypt_media(encrypted_path, temporary)
    return FileResponse(temporary, media_type=row["media_type"] or "video/mp4", filename=f"{base}{ext}", background=BackgroundTask(temporary.unlink, missing_ok=True), headers={"Cache-Control": "private, no-store"})


_startup_job_tasks = set()


@app.on_event("startup")
async def resume_pending_jobs():
    with closing(db()) as con:
        pending = con.execute("SELECT id,source,media_path,quality FROM lectures WHERE status IN ('queued','processing') ORDER BY created_at").fetchall()
    for row in pending:
        media = Path(row["media_path"]) if row["media_path"] else None
        if media and media.exists():
            args = (row["id"], media, False)
        else:
            source = decrypt_text(row["source"])
            if source and supported_video_url(source):
                args = (row["id"], source, True, row["quality"] or "best")
            else:
                set_status(row["id"], "error", "Не удалось продолжить: исходное видео больше не найдено")
                continue
        task = asyncio.create_task(asyncio.to_thread(process_lecture, *args))
        _startup_job_tasks.add(task)
        task.add_done_callback(_startup_job_tasks.discard)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(ROOT / "app" / "static" / "index.html")
