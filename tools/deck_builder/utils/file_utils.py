# utils/file_utils.py
import os
import re
from transliterate import translit

def sanitize_filename(filename):
    """Транслитерирует и убирает пробелы из имени файла."""
    sanitized = translit(filename, 'ru', reversed=True)
    sanitized = re.sub(r'[\s]+', '_', sanitized)
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '', sanitized)
    return sanitized

def normalize_path(path):
    """Унифицирует слеши в пути."""
    return os.path.normpath(path).replace('\\', '/')