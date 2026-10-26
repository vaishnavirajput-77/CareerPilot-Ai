from io import BytesIO
from pypdf import PdfReader

MAX_BYTES = 5 * 1024 * 1024

def extract_resume_text(filename: str, content: bytes) -> str:
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > MAX_BYTES:
        raise ValueError("File is too large. Maximum allowed size is 5 MB.")
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "txt":
        text = content.decode("utf-8", errors="replace")
    elif suffix == "pdf":
        try:
            reader = PdfReader(BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise ValueError("Could not read this PDF. Please try another text-based PDF.") from exc
    else:
        raise ValueError("Unsupported file type. Upload a PDF or TXT file.")
    text = text.strip()
    if not text:
        raise ValueError("No selectable text found. Scanned PDFs need OCR, which is not enabled in this version.")
    return text[:50000]
