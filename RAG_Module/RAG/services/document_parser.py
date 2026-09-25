from pathlib import Path
import fitz
from docx import Document as DocxDocument

def extract_text(file):
    extension=Path(file.name).suffix.lower()

    if extension ==".txt" or extension == ".md":
        return file.read().decode("utf-8")

    if extension == ".pdf":
        pdf=fitz.open(stream=file.read(),filetype="pdf")
        return "\n".join(page.get_text() for page in pdf)
    if extension == ".docx":
        document=DocxDocument(file)  
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    raise ValueError("unsupported file type")
   