import os
import base64

EXCLUDE_PATTERNS = ['.git', 'node_modules', '__pycache__', 'venv', '.DS_Store', '.mypy_cache']
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

def is_binary(content: bytes) -> bool:
    textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
    return bool(content.translate(None, textchars))

def should_exclude(file_path: str) -> bool:
    return any(pattern in file_path for pattern in EXCLUDE_PATTERNS)

def is_large(file_path: str) -> bool:
    return os.path.getsize(file_path) > MAX_FILE_SIZE 