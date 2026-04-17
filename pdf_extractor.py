import fitz        # PyMuPDF
import io

# Tesseract via pytesseract — only imported if needed (graceful fallback if not installed)
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_pdf_text(file_storage) -> tuple:
    """
    Extracts plain text from an uploaded PDF file.
    Sprint 4 Task 9: Scanned pages are now automatically handled via Tesseract OCR
    instead of being skipped with a warning.

    Strategy per page:
      1. Try PyMuPDF digital text extraction first (fast, accurate).
      2. If a page returns no text (scanned/image-based), rasterize it and run
         Tesseract OCR — transparent to the caller, same output format.
      3. If Tesseract is not installed, fall back to the old warning behaviour.

    Args:
        file_storage: Flask FileStorage object from request.files

    Returns:
        tuple: (extracted_text: str, warning: str)
        - extracted_text: full text content from all pages (digital + OCR)
        - warning: informational message about OCR usage, or "" if all digital
    """

    try:
        pdf_bytes = file_storage.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        extracted_pages = []   # pages with text (digital or OCR)
        ocr_pages       = []   # page numbers that needed OCR
        failed_pages    = []   # pages where even OCR got nothing

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text().strip()

            if text:
                # Digital text extracted cleanly — no OCR needed
                extracted_pages.append(f"[Page {page_num + 1}]\n{text}")

            else:
                # Blank page — likely scanned image
                if OCR_AVAILABLE:
                    ocr_text = _ocr_page(page, page_num + 1)
                    if ocr_text:
                        extracted_pages.append(f"[Page {page_num + 1} — OCR]\n{ocr_text}")
                        ocr_pages.append(page_num + 1)
                        print(f"[pdf_extractor] Page {page_num + 1}: OCR extracted {len(ocr_text)} chars")
                    else:
                        failed_pages.append(page_num + 1)
                        print(f"[pdf_extractor] Page {page_num + 1}: OCR returned no text")
                else:
                    # Tesseract not installed — treat as before (no text, warn)
                    failed_pages.append(page_num + 1)

        doc.close()

        full_text = "\n\n".join(extracted_pages)
        warning   = _build_warning(ocr_pages, failed_pages, OCR_AVAILABLE)

        return full_text, warning

    except Exception as e:
        print(f"[pdf_extractor] Error: {e}")
        return "", "PDF could not be read. Generating based on subject and grade instead."


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ocr_page(page, page_label: int) -> str:
    """
    Rasterizes a single fitz Page to a PIL Image and runs Tesseract OCR on it.

    Args:
        page:       fitz.Page object
        page_label: 1-based page number (for logging only)

    Returns:
        OCR-extracted text string, or "" if nothing found
    """
    try:
        # Render at 2x resolution (dpi=144) for better OCR accuracy
        mat  = fitz.Matrix(2, 2)
        pix  = page.get_pixmap(matrix=mat)
        img  = Image.open(io.BytesIO(pix.tobytes("png")))

        ocr_text = pytesseract.image_to_string(img, lang="eng")
        return ocr_text.strip()

    except Exception as e:
        print(f"[pdf_extractor] OCR failed on page {page_label}: {e}")
        return ""


def _build_warning(ocr_pages: list, failed_pages: list, ocr_available: bool) -> str:
    """
    Builds a human-readable warning string based on OCR outcomes.
    Returns "" (no warning) if everything extracted cleanly.
    """

    if not ocr_pages and not failed_pages:
        # All pages were digital — no warning needed
        return ""

    parts = []

    if ocr_pages:
        page_list = ", ".join(str(p) for p in ocr_pages)
        parts.append(
            f"Page(s) {page_list} were image-based and were processed using OCR. "
            f"Accuracy depends on image quality."
        )

    if failed_pages and ocr_available:
        page_list = ", ".join(str(p) for p in failed_pages)
        parts.append(
            f"Page(s) {page_list} could not be read even with OCR "
            f"(possibly blank or very low quality images)."
        )

    if failed_pages and not ocr_available:
        page_list = ", ".join(str(p) for p in failed_pages)
        parts.append(
            f"Page(s) {page_list} are image-based but Tesseract OCR is not installed. "
            f"Install it with: pip install pytesseract && apt install tesseract-ocr"
        )

    return " ".join(parts)