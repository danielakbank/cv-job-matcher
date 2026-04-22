import pdfplumber
import docx
import logging
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_text_from_pdf(uploaded_file) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        uploaded_file: A file-like object (e.g. from Streamlit uploader)
    
    Returns:
        Extracted text as a string, or empty string if extraction fails
    """
    text_parts = []

    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                else:
                    logger.warning(f"Page {i + 1} returned no text — may be a scanned image.")
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        raise ValueError(f"Could not read PDF file. Ensure it is not password-protected or corrupted.") from e

    return "\n".join(text_parts).strip()


def extract_text_from_docx(uploaded_file) -> str:
    """
    Extract text from a .docx Word document.

    Args:
        uploaded_file: A file-like object (e.g. from Streamlit uploader)

    Returns:
        Extracted text as a string, or empty string if extraction fails
    """
    text_parts = []

    try:
        file_bytes = BytesIO(uploaded_file.read())
        doc = docx.Document(file_bytes)

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text.strip())

    except Exception as e:
        logger.error(f"Failed to extract text from DOCX: {e}")
        raise ValueError(f"Could not read Word document. Ensure it is a valid .docx file.") from e

    return "\n".join(text_parts).strip()


def extract_cv_text(uploaded_file) -> str:
    """
    Main entry point. Detects file type and extracts CV text accordingly.

    Args:
        uploaded_file: A file-like object with a .name attribute (from Streamlit)

    Returns:
        Extracted text as a string

    Raises:
        ValueError: If the file type is unsupported or extraction fails
    """
    if uploaded_file is None:
        raise ValueError("No file was provided.")

    filename = uploaded_file.name.lower().strip()

    if filename.endswith(".pdf"):
        logger.info(f"Processing PDF: {uploaded_file.name}")
        return extract_text_from_pdf(uploaded_file)

    elif filename.endswith(".docx"):
        logger.info(f"Processing DOCX: {uploaded_file.name}")
        return extract_text_from_docx(uploaded_file)

    else:
        raise ValueError(
            f"Unsupported file type: '{uploaded_file.name}'. "
            "Please upload a PDF or Word (.docx) file."
        )