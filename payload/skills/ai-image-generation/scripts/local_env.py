from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
from ctypes import wintypes

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None


SKILL_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = Path.cwd()
LOCAL_ENV_FILE_VAR = "IMAGE_GENERATION_ENV_FILE"
LEGACY_LOCAL_ENV_FILE_VAR = "VIDEO_WORKFLOW_ENV_FILE"
_LOADED_FLAG = "_AI_IMAGE_GENERATION_LOCAL_ENV_LOADED"
WINDOWS_USER_ENV_KEYS = [
    "DASHSCOPE_API_KEY",
    "BEEAPI_API_KEY",
    "BEEAPI_IMAGE_API_KEY",
    "BEEAPI_GROK_API_KEY",
    "OPENAI_API_KEY",
    "GROK_IMAGE_API_KEY",
    "GROK_IMAGE_QUALITY_API_KEY",
    "VOLCENGINE_TTS_APP_ID",
    "VOLCENGINE_TTS_ACCESS_KEY",
    "VOLCENGINE_TTS_ACCESS_TOKEN",
    "VOLCENGINE_TTS_SECRET_KEY",
    "VOLCENGINE_TTS_2_API_KEY",
]


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _candidate_env_files() -> list[Path]:
    candidates: list[Path] = []

    raw_custom = os.environ.get(LOCAL_ENV_FILE_VAR, "").strip() or os.environ.get(LEGACY_LOCAL_ENV_FILE_VAR, "").strip()
    if raw_custom:
        for item in raw_custom.split(os.pathsep):
            item = item.strip()
            if item:
                candidates.append(Path(item))

    candidates.extend(
        [
            WORKSPACE_ROOT / ".local" / "secrets" / "workflow.env",
            WORKSPACE_ROOT / ".local" / "workflow.env",
            WORKSPACE_ROOT / ".local" / "secrets" / "personal_env.secure.json",
            SKILL_ROOT / ".local" / "secrets" / "workflow.env",
            SKILL_ROOT / ".local" / "secrets" / "personal_env.secure.json",
        ]
    )

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate.resolve() if candidate.is_absolute() else (WORKSPACE_ROOT / candidate).resolve())
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(Path(normalized))
    return deduped


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return key, value


def load_local_env(*, override: bool = False) -> dict[str, str]:
    loaded_from: dict[str, str] = {}
    for env_file in _candidate_env_files():
        if not env_file.exists():
            continue
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(raw_line)
            if not parsed:
                continue
            key, value = parsed
            if not override and os.environ.get(key):
                continue
            os.environ[key] = value
            loaded_from[key] = str(env_file)
    loaded_from.update(load_secure_env(override=override))
    loaded_from.update(load_windows_user_env(override=override))
    return loaded_from


def load_windows_user_env(*, override: bool = False) -> dict[str, str]:
    if os.name != "nt" or winreg is None:
        return {}
    loaded_from: dict[str, str] = {}
    try:
        env_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
    except OSError:
        return {}

    try:
        for key in WINDOWS_USER_ENV_KEYS:
            if not override and os.environ.get(key):
                continue
            try:
                value, _ = winreg.QueryValueEx(env_key, key)
            except FileNotFoundError:
                continue
            if not value:
                continue
            os.environ[key] = str(value)
            loaded_from[key] = "HKCU\\Environment"
    finally:
        winreg.CloseKey(env_key)
    return loaded_from


def _blob_from_bytes(data: bytes) -> tuple[DATA_BLOB, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(data)
    blob = DATA_BLOB(
        cbData=len(data),
        pbData=ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)),
    )
    return blob, buffer


def _unprotect_windows_dpapi(ciphertext: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("secure env decrypt is only supported on Windows")

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt_unprotect_data = crypt32.CryptUnprotectData
    crypt_unprotect_data.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    crypt_unprotect_data.restype = wintypes.BOOL

    local_free = kernel32.LocalFree
    local_free.argtypes = [wintypes.HLOCAL]
    local_free.restype = wintypes.HLOCAL

    in_blob, in_buffer = _blob_from_bytes(ciphertext)
    out_blob = DATA_BLOB()
    if not crypt_unprotect_data(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise ctypes.WinError()

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        del in_buffer
        if out_blob.pbData:
            local_free(out_blob.pbData)


def _decode_secure_payload(scheme: str, encrypted_value: str) -> str:
    normalized_scheme = (scheme or "windows-securestring-v1").strip().lower()
    raw_value = encrypted_value.strip()
    if normalized_scheme == "windows-securestring-v1":
        ciphertext = bytes.fromhex(raw_value)
        plaintext = _unprotect_windows_dpapi(ciphertext)
        return plaintext.decode("utf-16-le")
    if normalized_scheme == "windows-dpapi-base64-v1":
        import base64

        ciphertext = base64.b64decode(raw_value)
        plaintext = _unprotect_windows_dpapi(ciphertext)
        return plaintext.decode("utf-8")
    raise RuntimeError(f"unsupported secure env scheme: {scheme}")


def load_secure_env_file(path: Path, *, override: bool = False) -> dict[str, str]:
    if not path.exists() or path.suffix.lower() != ".json":
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    scheme = str(payload.get("scheme", "windows-securestring-v1"))
    entries = payload.get("entries", {})
    loaded_from: dict[str, str] = {}
    for key, encrypted_value in entries.items():
        if not override and os.environ.get(key):
            continue
        if os.name != "nt":
            continue
        value = _decode_secure_payload(scheme, str(encrypted_value))
        os.environ[key] = value
        loaded_from[key] = str(path)
    return loaded_from


def load_secure_env(*, override: bool = False) -> dict[str, str]:
    loaded_from: dict[str, str] = {}
    for env_file in _candidate_env_files():
        loaded_from.update(load_secure_env_file(env_file, override=override))
    return loaded_from


def ensure_local_env_loaded(*, override: bool = False) -> dict[str, str]:
    if os.environ.get(_LOADED_FLAG) == "1" and not override:
        return {}
    loaded = load_local_env(override=override)
    os.environ[_LOADED_FLAG] = "1"
    return loaded
