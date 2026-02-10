# OCR Setup Guide

## Overview

OCR (Optical Character Recognition) has been added as a final fallback for PDF text extraction. This handles:
- ✅ Scanned PDFs (images of documents)
- ✅ PDFs with non-standard font encoding
- ✅ PDFs where normal text extraction returns garbage

## Installation Steps

### 1. Install Python Dependencies

Already done! The following packages are now in `requirements.txt`:
```bash
pip install pytesseract pdf2image pillow
```

### 2. Install Tesseract OCR (System Dependency)

#### Windows Installation

**Option A: Direct Download (Recommended)**
1. Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (tesseract-ocr-w64-setup-*.exe)
3. Install to default location: `C:\Program Files\Tesseract-OCR`
4. The code will automatically find it in this location

**Option B: Using Chocolatey**
```powershell
choco install tesseract
```

**Option C: Using Scoop**
```powershell
scoop install tesseract
```

#### Linux Installation

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install poppler-utils  # For pdf2image
```

**CentOS/RHEL:**
```bash
sudo yum install tesseract
sudo yum install poppler-utils
```

#### macOS Installation

```bash
brew install tesseract
brew install poppler  # For pdf2image
```

### 3. Verify Installation

```bash
tesseract --version
```

Should output something like:
```
tesseract 5.x.x
```

### 4. Test OCR in Python

```python
import pytesseract
from pdf2image import convert_from_path

# Check version
print(pytesseract.get_tesseract_version())
```

## How It Works

The extraction strategy now includes OCR as the **final fallback**:

1. PyMuPDF (fitz) - fast, reliable ✓
2. PyPDF2 - standard PDFs ✓
3. pdfplumber (default) ✓
4. pdfplumber (tolerance) ✓
5. pdfminer.six ✓
6. **OCR (pytesseract)** - NEW! 🆕

### OCR Process

When all text extraction methods fail validation:

```
1. Convert PDF to images (300 DPI)
   └─> Each page becomes a high-res image

2. Run Tesseract OCR on each image
   └─> Extract text from the image

3. Validate extracted text
   └─> Check if readable and valid

4. Return OCR text or error
   └─> Success or detailed error message
```

## Performance Notes

**OCR is SLOW compared to text extraction:**
- Text extraction: ~0.5 seconds per page
- OCR extraction: ~3-5 seconds per page

This is why OCR is the **last resort** - only used when all other methods fail.

## Configuration

### Custom Tesseract Path

If Tesseract is installed in a non-standard location, set the path in your code or environment:

```python
# In pdf.py or via environment variable
pytesseract.pytesseract.tesseract_cmd = r"C:\Custom\Path\tesseract.exe"
```

### Adjust OCR Quality

The `extract_with_ocr()` function accepts a `dpi` parameter:
- **150 DPI**: Faster, lower quality
- **300 DPI**: Default, good balance ✓
- **600 DPI**: Slower, best quality

## Troubleshooting

### Error: "Tesseract not found"

**Fix:**
1. Install Tesseract (see installation steps above)
2. Restart your application
3. Verify with: `tesseract --version`

### Error: "pdf2image requires poppler"

**Windows:**
- Download poppler: https://github.com/oschwartz10612/poppler-windows/releases
- Extract to `C:\Program Files\poppler`
- Add `C:\Program Files\poppler\Library\bin` to PATH

**Linux/Mac:**
```bash
# Linux
sudo apt-get install poppler-utils

# Mac
brew install poppler
```

### OCR Returns Garbage Text

**Possible causes:**
- PDF quality too low
- Handwritten text (Tesseract only works on printed text)
- Complex layouts or tables

**Solutions:**
- Use higher DPI (600 instead of 300)
- Clean/pre-process the PDF
- Use a scanned PDF with better quality

### OCR is Too Slow

**Options:**
1. Reduce DPI to 150 (faster but less accurate)
2. Process in background/async
3. Cache OCR results
4. Consider using cloud OCR service (Google Vision, AWS Textract)

## Testing

### Test with Normal PDF
```bash
# Should use PyMuPDF (fast)
curl -X POST http://localhost:8000/api/contracts/upload \
  -F "file=@normal.pdf" \
  -F "project_id=123"
```

### Test with Scanned PDF
```bash
# Should fall back to OCR (slow but works)
curl -X POST http://localhost:8000/api/contracts/upload \
  -F "file=@scanned.pdf" \
  -F "project_id=123"
```

### Test with Bad Font Encoding
```bash
# Should detect corrupted text, fall back to OCR
curl -X POST http://localhost:8000/api/contracts/upload \
  -F "file=@bad_fonts.pdf" \
  -F "project_id=123"
```

## Advanced OCR Features (Future)

### Language Support

Tesseract supports 100+ languages. To use other languages:

```bash
# Install language packs
tesseract --list-langs  # See installed languages

# Download more languages
# Windows: Use installer options
# Linux: sudo apt-get install tesseract-ocr-[lang]
```

```python
# In extract_with_ocr()
page_text = pytesseract.image_to_string(image, lang='spa')  # Spanish
page_text = pytesseract.image_to_string(image, lang='fra')  # French
```

### OCR Configuration

Fine-tune OCR with config options:

```python
custom_config = r'--oem 3 --psm 6'
page_text = pytesseract.image_to_string(image, config=custom_config)
```

- `--oem 3`: Use LSTM neural network (best)
- `--psm 6`: Assume uniform block of text

## Files Modified

1. `api/services/pdf.py`
   - Added OCR imports and availability check
   - Added `extract_with_ocr()` function
   - Integrated OCR as Strategy 6
   - Auto-detects Tesseract path on Windows

2. `requirements.txt`
   - Added `pytesseract>=0.3.10`
   - Added `pdf2image>=1.16.0`
   - Added `pillow>=10.0.0`

## Benefits

✅ **Handles scanned PDFs** - No more "unable to extract text" errors
✅ **Fixes font encoding issues** - OCR sees the visual text, not the encoding
✅ **Graceful fallback** - Fast methods tried first, OCR only when needed
✅ **Clear error messages** - Tells user if OCR is unavailable
✅ **Production ready** - Works without Tesseract (just skips OCR step)

## Cost Considerations

OCR is compute-intensive:
- Higher CPU usage
- Longer processing time
- More memory usage

Consider:
- Running on a dedicated worker/queue
- Caching OCR results
- Setting timeouts for large documents
- Using async processing for user experience
