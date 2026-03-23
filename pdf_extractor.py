import fitz  # PyMuPDF

def extract_pdf_text(file_storage) -> tuple:
    """
    Extracts plain text from an uploaded PDF file.

    Args:
        file_storage: Flask FileStorage object from request.files

    Returns:
        tuple: (extracted_text: str, warning: str)
        - extracted_text: full text content, or "" if scanned/failed
        - warning: message to show user if extraction failed, or "" if all good
    """

    try:
        pdf_bytes = file_storage.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        extracted_pages = []
        scanned_pages   = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text().strip()

            if text:
                extracted_pages.append(f"[Page {page_num + 1}]\n{text}")
            else:
                scanned_pages += 1

        doc.close()

        total_pages = len(extracted_pages) + scanned_pages

        # All pages are blank — scanned PDF
        if scanned_pages == total_pages:
            warning = (
                f"The uploaded PDF appears to be a scanned image-based PDF "
                f"({total_pages} page(s)). Text could not be extracted. "
                f"Generating based on subject and grade instead."
            )
            return "", warning

        # Some pages extracted, some scanned — partial extraction
        if scanned_pages > 0:
            warning = (
                f"Warning: {scanned_pages} of {total_pages} page(s) are image-based "
                f"and could not be read. Questions are based on the extracted text only."
            )
            return "\n\n".join(extracted_pages), warning

        # All pages extracted successfully
        return "\n\n".join(extracted_pages), ""

    except Exception as e:
        print(f"[pdf_extractor] Error: {e}")
        return "", "PDF could not be read. Generating based on subject and grade instead."