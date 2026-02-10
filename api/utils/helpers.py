from typing import Dict, Any, List
from datetime import datetime, timedelta
import hashlib
import secrets

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token
    """
    return secrets.token_urlsafe(length)

def hash_string(text: str) -> str:
    """
    Create SHA256 hash of a string
    """
    return hashlib.sha256(text.encode()).hexdigest()

def format_datetime(dt: datetime, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime object to string
    """
    return dt.strftime(format_string)

def parse_datetime(date_string: str, format_string: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse string to datetime object
    """
    return datetime.strptime(date_string, format_string)

def calculate_date_difference(date1: datetime, date2: datetime) -> int:
    """
    Calculate difference in days between two dates
    """
    return abs((date2 - date1).days)

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to remove potentially dangerous characters
    """
    # Remove path separators and other dangerous characters
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    sanitized = filename
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    return sanitized

def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Check if file has an allowed extension
    """
    return any(filename.lower().endswith(ext.lower()) for ext in allowed_extensions)

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length with suffix
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract important keywords from text (simple implementation)
    """
    # Remove common words and split
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    words = text.lower().split()
    keywords = [word for word in words if word not in common_words and len(word) > 3]

    # Count frequency
    word_freq = {}
    for word in keywords:
        word_freq[word] = word_freq.get(word, 0) + 1

    # Sort by frequency and return top keywords
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_keywords[:max_keywords]]
