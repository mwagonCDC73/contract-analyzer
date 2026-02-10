import pdfplumber
from io import BytesIO
from typing import Dict, List
import logging
import os

# Import multiple PDF libraries for fallback strategies
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False

# OCR libraries
try:
    import pytesseract
    from pdf2image import convert_from_bytes
    from PIL import Image
    OCR_AVAILABLE = True

    # Try to find Tesseract executable on Windows
    if os.name == 'nt':  # Windows
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)

def is_valid_text(text: str) -> tuple[bool, str]:
    """
    Comprehensive validation to check if extracted text is readable and usable.

    Args:
        text: Extracted text to validate

    Returns:
        Tuple of (is_valid: bool, reason: str)
    """
    if not text:
        return False, "No text extracted"

    if len(text) < 100:
        return False, f"Text too short ({len(text)} chars) - likely extraction failure"

    # Check for CID patterns (font encoding issues)
    if "(cid:" in text:
        cid_count = text.count("(cid:")
        cid_ratio = (cid_count / len(text)) * 1000
        if cid_ratio > 5:
            return False, f"High CID pattern density ({cid_count} patterns) indicates font encoding issues"

    # Check for excessive forward slashes (common in corrupted PDFs)
    slash_count = text.count("/")
    slash_ratio = slash_count / len(text)
    if slash_ratio > 0.1:
        return False, f"Excessive forward slashes ({slash_ratio:.1%}) indicates corrupted extraction"

    # Check alphanumeric ratio - text should be mostly readable characters
    # Count alphanumeric, spaces, and common punctuation as "valid"
    valid_chars = sum(
        c.isalnum() or c.isspace() or c in ".,;:!?-()[]{}\"'@#$%&*+=<>/"
        for c in text
    )
    valid_ratio = valid_chars / len(text)

    if valid_ratio < 0.5:
        return False, f"Low readable character ratio ({valid_ratio:.1%}) indicates corrupted text"

    # Check for reasonable word formation
    words = text.split()
    if len(words) < 10:
        return False, f"Too few words ({len(words)}) - likely extraction failure"

    # Check average word length (corrupted text often has very short or very long "words")
    avg_word_len = sum(len(w) for w in words) / len(words)
    if avg_word_len < 2 or avg_word_len > 20:
        return False, f"Abnormal average word length ({avg_word_len:.1f}) indicates corruption"

    return True, "Text appears valid"

def is_garbled(text: str) -> bool:
    """
    Legacy function for backwards compatibility.
    Check if extracted text contains garbled characters.

    Args:
        text: Extracted text to check

    Returns:
        True if text appears garbled
    """
    is_valid, _ = is_valid_text(text)
    return not is_valid

def extract_with_pymupdf(pdf_content: bytes) -> str:
    """Extract text using PyMuPDF (fitz) - most reliable for complex PDFs"""
    try:
        logger.info("[PDF] Trying PyMuPDF (fitz) extraction...")
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        text = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n\n"
        doc.close()
        logger.info(f"[PDF] PyMuPDF extracted {len(text)} characters")
        return text.strip()
    except Exception as e:
        logger.warning(f"[PDF] PyMuPDF extraction failed: {e}")
        return ""

def extract_with_pypdf2(pdf_content: bytes) -> str:
    """Extract text using PyPDF2"""
    try:
        logger.info("[PDF] Trying PyPDF2 extraction...")
        file = BytesIO(pdf_content)
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
        logger.info(f"[PDF] PyPDF2 extracted {len(text)} characters")
        return text.strip()
    except Exception as e:
        logger.warning(f"[PDF] PyPDF2 extraction failed: {e}")
        return ""

def extract_with_pdfplumber(pdf_content: bytes, use_tolerance: bool = False) -> str:
    """Extract text using pdfplumber with optional tolerance settings"""
    try:
        method = "pdfplumber (with tolerance)" if use_tolerance else "pdfplumber (default)"
        logger.info(f"[PDF] Trying {method} extraction...")

        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            text = ""
            for page in pdf.pages:
                if use_tolerance:
                    # Use tolerance settings to handle spacing issues
                    page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                else:
                    page_text = page.extract_text()

                if page_text:
                    text += page_text + "\n\n"

        logger.info(f"[PDF] {method} extracted {len(text)} characters")
        return text.strip()
    except Exception as e:
        logger.warning(f"[PDF] {method} extraction failed: {e}")
        return ""

def extract_with_pdfminer(pdf_content: bytes) -> str:
    """Extract text using pdfminer.six"""
    try:
        logger.info("[PDF] Trying pdfminer.six extraction...")
        file = BytesIO(pdf_content)
        text = pdfminer_extract(file)
        logger.info(f"[PDF] pdfminer.six extracted {len(text)} characters")
        return text.strip()
    except Exception as e:
        logger.warning(f"[PDF] pdfminer.six extraction failed: {e}")
        return ""

def extract_with_ocr(pdf_content: bytes, dpi: int = 300) -> str:
    """
    Extract text using OCR (Optical Character Recognition).
    This is a fallback for scanned PDFs or PDFs with non-standard font encoding.

    Args:
        pdf_content: Binary content of the PDF file
        dpi: DPI for image conversion (higher = better quality but slower)

    Returns:
        Extracted text from OCR
    """
    if not OCR_AVAILABLE:
        logger.warning("[PDF] OCR libraries not available (pytesseract/pdf2image not installed)")
        return ""

    try:
        logger.info("[PDF] Trying OCR extraction (this may take a moment)...")

        # Test if tesseract is actually available
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            logger.warning(f"[PDF] Tesseract OCR not installed or not found in PATH: {e}")
            logger.warning("[PDF] Install from: https://github.com/UB-Mannheim/tesseract/wiki")
            return ""

        # Convert PDF pages to images
        logger.info(f"[PDF] Converting PDF to images at {dpi} DPI...")
        images = convert_from_bytes(pdf_content, dpi=dpi)
        logger.info(f"[PDF] Converted {len(images)} pages to images")

        # Run OCR on each page
        text = ""
        for i, image in enumerate(images):
            logger.info(f"[PDF] Running OCR on page {i + 1}/{len(images)}...")
            page_text = pytesseract.image_to_string(image, lang='eng')
            if page_text:
                text += page_text + "\n\n"

        logger.info(f"[PDF] OCR extracted {len(text)} characters from {len(images)} pages")
        return text.strip()

    except Exception as e:
        logger.warning(f"[PDF] OCR extraction failed: {e}")
        return ""

def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract text from a PDF file using multiple strategies with automatic fallback.

    This function validates extracted text quality and raises an error if no valid
    text can be extracted, preventing corrupted text from being sent to Claude API.

    Strategy order:
    1. Try PyMuPDF (fitz) - most reliable for complex PDFs
    2. Try PyPDF2 (good for standard native PDFs)
    3. Try pdfplumber with default settings
    4. Try pdfplumber with tolerance settings
    5. Try pdfminer.six
    6. Try OCR (pytesseract) - for scanned PDFs or non-standard font encoding

    Args:
        pdf_content: Binary content of the PDF file

    Returns:
        Extracted text as a string (guaranteed to be valid/readable)

    Raises:
        Exception: If text extraction fails or all extractions produce corrupted text
    """
    logger.info("[PDF] Starting multi-strategy PDF extraction with validation")

    best_text = ""
    best_method = "none"
    extraction_attempts = []

    # Strategy 1: Try PyMuPDF first (most reliable for complex PDFs)
    if PYMUPDF_AVAILABLE:
        text = extract_with_pymupdf(pdf_content)
        if text:
            is_valid, reason = is_valid_text(text)
            if is_valid:
                logger.info("[PDF] ✓ PyMuPDF extraction successful - text validated")
                return text
            else:
                logger.warning(f"[PDF] ✗ PyMuPDF extracted text failed validation: {reason}")
                extraction_attempts.append(f"PyMuPDF: {reason}")
                if len(text) > len(best_text):
                    best_text = text
                    best_method = "PyMuPDF"

    # Strategy 2: Try PyPDF2
    if PYPDF2_AVAILABLE:
        text = extract_with_pypdf2(pdf_content)
        if text:
            is_valid, reason = is_valid_text(text)
            if is_valid:
                logger.info("[PDF] ✓ PyPDF2 extraction successful - text validated")
                return text
            else:
                logger.warning(f"[PDF] ✗ PyPDF2 extracted text failed validation: {reason}")
                extraction_attempts.append(f"PyPDF2: {reason}")
                if len(text) > len(best_text):
                    best_text = text
                    best_method = "PyPDF2"

    # Strategy 3: Try pdfplumber default
    text = extract_with_pdfplumber(pdf_content, use_tolerance=False)
    if text:
        is_valid, reason = is_valid_text(text)
        if is_valid:
            logger.info("[PDF] ✓ pdfplumber (default) extraction successful - text validated")
            return text
        else:
            logger.warning(f"[PDF] ✗ pdfplumber (default) failed validation: {reason}")
            extraction_attempts.append(f"pdfplumber (default): {reason}")
            if len(text) > len(best_text):
                best_text = text
                best_method = "pdfplumber (default)"

    # Strategy 4: Try pdfplumber with tolerance settings
    text = extract_with_pdfplumber(pdf_content, use_tolerance=True)
    if text:
        is_valid, reason = is_valid_text(text)
        if is_valid:
            logger.info("[PDF] ✓ pdfplumber (tolerance) extraction successful - text validated")
            return text
        else:
            logger.warning(f"[PDF] ✗ pdfplumber (tolerance) failed validation: {reason}")
            extraction_attempts.append(f"pdfplumber (tolerance): {reason}")
            if len(text) > len(best_text):
                best_text = text
                best_method = "pdfplumber (tolerance)"

    # Strategy 5: Try pdfminer.six
    if PDFMINER_AVAILABLE:
        text = extract_with_pdfminer(pdf_content)
        if text:
            is_valid, reason = is_valid_text(text)
            if is_valid:
                logger.info("[PDF] ✓ pdfminer.six extraction successful - text validated")
                return text
            else:
                logger.warning(f"[PDF] ✗ pdfminer.six failed validation: {reason}")
                extraction_attempts.append(f"pdfminer.six: {reason}")
                if len(text) > len(best_text):
                    best_text = text
                    best_method = "pdfminer.six"

    # Strategy 6: Try OCR as final fallback (for scanned PDFs or non-standard fonts)
    if OCR_AVAILABLE:
        logger.info("[PDF] All text extraction methods failed - trying OCR as last resort...")
        text = extract_with_ocr(pdf_content, dpi=300)
        if text:
            is_valid, reason = is_valid_text(text)
            if is_valid:
                logger.info("[PDF] ✓ OCR extraction successful - text validated")
                logger.info("[PDF] Note: OCR was required, indicating the PDF may be scanned or have font encoding issues")
                return text
            else:
                logger.warning(f"[PDF] ✗ OCR extraction failed validation: {reason}")
                extraction_attempts.append(f"OCR: {reason}")
                if len(text) > len(best_text):
                    best_text = text
                    best_method = "OCR"

    # CRITICAL: Do NOT return corrupted text - raise error instead
    error_details = "\n".join(f"  - {attempt}" for attempt in extraction_attempts)

    if best_text:
        logger.error(
            f"[PDF] ✗ EXTRACTION FAILED - All methods produced corrupted text\n"
            f"Best attempt: {best_method} ({len(best_text)} chars)\n"
            f"Failures:\n{error_details}"
        )
        raise Exception(
            f"PDF text extraction failed: All extraction methods (including OCR) produced corrupted or unreadable text. "
            f"This PDF may have severe encoding issues or be corrupted. "
            f"Please verify the PDF is valid and try again."
        )
    else:
        logger.error(f"[PDF] ✗ EXTRACTION FAILED - No text extracted by any method")
        ocr_note = " (OCR not available - install Tesseract)" if not OCR_AVAILABLE else ""
        raise Exception(
            f"PDF text extraction failed: Unable to extract any text from the PDF{ocr_note}. "
            f"This file may be encrypted, corrupted, or completely blank."
        )

def extract_tables_from_pdf(pdf_content: bytes) -> List[List[List[str]]]:
    """
    Extract tables from a PDF file

    Args:
        pdf_content: Binary content of the PDF file

    Returns:
        List of tables, where each table is a list of rows
    """
    try:
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            all_tables = []
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)

            return all_tables
    except Exception as e:
        raise Exception(f"Failed to extract tables from PDF: {str(e)}")

def get_pdf_metadata(pdf_content: bytes) -> Dict:
    """
    Extract metadata from a PDF file

    Args:
        pdf_content: Binary content of the PDF file

    Returns:
        Dictionary containing PDF metadata
    """
    try:
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            metadata = {
                "pages": len(pdf.pages),
                "metadata": pdf.metadata
            }

            return metadata
    except Exception as e:
        raise Exception(f"Failed to extract PDF metadata: {str(e)}")
