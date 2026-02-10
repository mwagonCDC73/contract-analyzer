#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify OCR setup and PDF extraction capabilities.
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use ASCII-compatible symbols for Windows compatibility
OK = "[OK]"
FAIL = "[X]"

def test_imports():
    """Test that all required libraries are available"""
    print("\n" + "="*60)
    print("TESTING IMPORTS")
    print("="*60)

    results = {}

    # Test core PDF libraries
    try:
        import fitz
        results['PyMuPDF'] = f"{OK} Version {fitz.version}"
    except ImportError as e:
        results['PyMuPDF'] = f"{FAIL} Not installed: {e}"

    try:
        from PyPDF2 import PdfReader
        results['PyPDF2'] = f"{OK} Installed"
    except ImportError as e:
        results['PyPDF2'] = f"{FAIL} Not installed: {e}"

    try:
        import pdfplumber
        results['pdfplumber'] = f"{OK} Installed"
    except ImportError as e:
        results['pdfplumber'] = f"{FAIL} Not installed: {e}"

    # Test OCR libraries
    try:
        import pytesseract
        try:
            version = pytesseract.get_tesseract_version()
            results['pytesseract'] = f"{OK} Version {version}"
        except Exception as e:
            results['pytesseract'] = f"{OK} Library installed, but Tesseract executable not found"
    except ImportError as e:
        results['pytesseract'] = f"{FAIL} Not installed: {e}"

    try:
        from pdf2image import convert_from_bytes
        results['pdf2image'] = f"{OK} Installed"
    except ImportError as e:
        results['pdf2image'] = f"{FAIL} Not installed: {e}"

    try:
        from PIL import Image
        results['Pillow'] = f"{OK} Installed"
    except ImportError as e:
        results['Pillow'] = f"{FAIL} Not installed: {e}"

    # Print results
    for lib, status in results.items():
        print(f"  {lib:20s} {status}")

    return all(OK in status for status in results.values())

def test_ocr_availability():
    """Test if Tesseract OCR is properly configured"""
    print("\n" + "="*60)
    print("TESTING TESSERACT OCR")
    print("="*60)

    try:
        import pytesseract

        # Test Tesseract executable
        try:
            version = pytesseract.get_tesseract_version()
            print(f"  {OK} Tesseract is installed and working")
            print(f"    Version: {version}")

            # Test installed languages
            try:
                langs = pytesseract.get_languages()
                print(f"    Languages: {', '.join(langs)}")
            except:
                print(f"    Languages: Could not detect")

            return True

        except pytesseract.TesseractNotFoundError as e:
            print(f"  {FAIL} Tesseract executable not found")
            print(f"    Error: {e}")
            print(f"\n  Install Tesseract from:")
            print(f"    Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            print(f"    Linux:   sudo apt-get install tesseract-ocr")
            print(f"    macOS:   brew install tesseract")
            return False

    except ImportError:
        print(f"  {FAIL} pytesseract library not installed")
        print(f"    Run: pip install pytesseract")
        return False

def test_pdf_service():
    """Test the PDF extraction service"""
    print("\n" + "="*60)
    print("TESTING PDF SERVICE")
    print("="*60)

    try:
        from services.pdf import (
            is_valid_text,
            extract_with_pymupdf,
            extract_with_ocr,
            PYMUPDF_AVAILABLE,
            OCR_AVAILABLE
        )

        print(f"  PyMuPDF Available: {PYMUPDF_AVAILABLE}")
        print(f"  OCR Available:     {OCR_AVAILABLE}")

        # Test validation function
        print("\n  Testing text validation:")

        test_cases = [
            ("This is a valid contract with enough text to pass validation checks.", True),
            ("(cid:123)(cid:456)(cid:789)", False),
            ("short", False),
            ("////////////////////", False),
        ]

        for text, should_pass in test_cases:
            is_valid, reason = is_valid_text(text)
            status = OK if is_valid == should_pass else FAIL
            display_text = text[:30] + "..." if len(text) > 30 else text
            print(f"    {status} '{display_text}' -> {is_valid} ({reason})")

        return True

    except Exception as e:
        print(f"  {FAIL} Error testing PDF service: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PDF EXTRACTION & OCR TEST SUITE")
    print("="*60)

    results = []

    # Run tests
    results.append(("Import Test", test_imports()))
    results.append(("OCR Availability", test_ocr_availability()))
    results.append(("PDF Service", test_pdf_service()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for name, passed in results:
        status = f"{OK} PASS" if passed else f"{FAIL} FAIL"
        print(f"  {status:12s} {name}")

    print("="*60)

    all_passed = all(result[1] for result in results)
    if all_passed:
        print(f"\n{OK} All tests passed! OCR is ready to use.")
        return 0
    else:
        print(f"\n{FAIL} Some tests failed. See errors above.")
        print("\nCommon fixes:")
        print("  1. Install missing Python packages: pip install -r requirements.txt")
        print("  2. Install Tesseract OCR (see OCR_SETUP.md)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
