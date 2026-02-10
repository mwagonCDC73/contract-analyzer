# PDF Text Extraction Fix

## Problem
Claude was receiving corrupted text with special characters instead of readable contract text, causing:
- Wasted API costs on garbage text
- Failed contract analysis
- Poor user experience

## Solution Implemented

### 1. Enhanced Text Validation (`api/services/pdf.py`)

**New `is_valid_text()` function** with comprehensive checks:

```python
def is_valid_text(text: str) -> tuple[bool, str]:
    """Comprehensive validation to check if extracted text is readable"""
```

**Validation checks:**
- ✓ Minimum length (100 chars)
- ✓ CID pattern detection `(cid:XX)` - indicates font encoding issues
- ✓ Excessive forward slashes (> 10% of text)
- ✓ Alphanumeric ratio (must be > 50% readable characters)
- ✓ Word count validation (must have at least 10 words)
- ✓ Average word length check (2-20 chars, detects corruption)

### 2. Improved Extraction Strategy

**Priority order (with validation at each step):**
1. **PyMuPDF (fitz)** - most reliable for complex PDFs ✓
2. PyPDF2 - good for standard native PDFs
3. pdfplumber (default) - fallback option
4. pdfplumber (tolerance) - handles spacing issues
5. pdfminer.six - last resort

### 3. Critical: Error Handling

**BEFORE:** Returned corrupted text anyway, wasting API costs

**AFTER:** Raises descriptive error and prevents Claude API call:

```python
raise Exception(
    "PDF text extraction failed: All extraction methods produced corrupted or unreadable text. "
    "This PDF may use non-standard fonts, be scanned without OCR, or have encoding issues. "
    "Please ensure the PDF contains selectable text and try again."
)
```

### 4. User-Facing Error Messages

The error is caught in `api/routers/contracts.py:173` and returned to the user as:

```json
{
  "detail": "Failed to upload contract: PDF text extraction failed: ..."
}
```

**Users now get clear feedback instead of silent failures.**

## Dependencies Updated

Added to `requirements.txt`:
```
pymupdf>=1.23.0
```

**Installation:**
```bash
pip install -r requirements.txt
```

Or directly:
```bash
pip install pymupdf
```

## Testing

To verify the fix works:

1. **Test with valid PDF:**
   - Upload a normal contract PDF
   - Should extract cleanly and proceed to analysis

2. **Test with corrupted/scanned PDF:**
   - Upload a scanned PDF without OCR
   - Should return clear error message
   - Should NOT call Claude API

3. **Test with image-based PDF:**
   - Should fail with message: "Unable to extract any text from the PDF"
   - User knows to run OCR first

## Benefits

✅ **No more wasted API costs** on corrupted text
✅ **Clear error messages** guide users to fix issues
✅ **PyMuPDF priority** improves extraction success rate
✅ **Validation prevents garbage** from reaching Claude
✅ **Better debugging** with detailed extraction logs

## Validation Examples

### Valid Text (Passes)
```
"This agreement made on January 1, 2024 between..."
```
- Clear words, good character ratio, no corruption patterns

### Invalid Text (Fails)
```
"(cid:123)(cid:456)/Type/Font/Subtype/TrueType..."
```
- High CID pattern count
- Excessive forward slashes
- Low alphanumeric ratio
- Fails validation → Error returned to user

## Files Modified

1. `api/services/pdf.py` - Enhanced validation and extraction
2. `requirements.txt` - Added PyMuPDF dependency
3. `api/routers/contracts.py` - Already had error handling (no changes needed)

## Next Steps

If issues persist with specific PDFs:
1. Check the logs for validation failure reasons
2. Consider adding OCR capability for scanned documents
3. May need to handle password-protected PDFs separately
