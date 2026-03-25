"""
PrescriptionParserAgent — OCR + HuggingFace Medical NER pipeline.

Parses uploaded prescription images or PDFs into structured medical data using:
1. pytesseract (OCR) for images, or pdfplumber for PDFs
2. HuggingFace d4data/biomedical-ner-all for named entity recognition
3. Heuristic regex for patient demographic extraction (age, gender)

The NER pipeline is expected to be loaded once at application startup and
injected as a parameter — this module never loads model weights itself.
"""

from __future__ import annotations

import io
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from transformers import Pipeline

from models.schemas import ExtractionResult, PatientInfo

# ---------------------------------------------------------------------------
# Optional dependencies
# ---------------------------------------------------------------------------

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import pdfplumber
    PDF_PLUMBER_AVAILABLE = True
except ImportError:
    PDF_PLUMBER_AVAILABLE = False

# ---------------------------------------------------------------------------
# Sentinel constant for extraction failure
# ---------------------------------------------------------------------------

# Returned by _ocr_image and _extract_pdf_text when extraction cannot proceed.
# Using a sentinel (rather than a human-readable string) lets parse_prescription
# distinguish a genuine failure from successfully extracted text.
_EXTRACTION_FAILED = "__EXTRACTION_FAILED__"

# ---------------------------------------------------------------------------
# NER entity-type to output-field mapping
# ---------------------------------------------------------------------------

# Maps the base label suffix (after B- / I- prefix) to ExtractionResult fields.
_LABEL_TO_FIELD: dict[str, str] = {
    "DISO": "diagnosis",   # disorder / diagnosis
    "CHEM": "medications", # chemical / medication
    "PROC": "procedure",   # procedure
}


# ---------------------------------------------------------------------------
# Module-level NER span helper (Fix 2: replaces nested _flush closure)
# ---------------------------------------------------------------------------

def _flush_span(field: str | None, tokens: list[str], result: dict[str, list[str]]) -> None:
    """
    Append the accumulated token span to the appropriate list in *result*.

    Takes explicit arguments instead of closing over mutable outer variables,
    making the logic easier to reason about and test in isolation.

    Args:
        field: The result-dict key to append to (e.g. "diagnosis"), or None.
        tokens: Accumulated word tokens for the current span.
        result: The dict being populated by _run_ner.
    """
    if field and tokens:
        entity_str = " ".join(tokens).strip()
        # Normalise whitespace and title-case for readability
        entity_str = re.sub(r"\s+", " ", entity_str).title()
        if entity_str and entity_str not in result[field]:
            result[field].append(entity_str)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ocr_image(file_bytes: bytes) -> str:
    """
    Run OCR on raw image bytes using pytesseract.

    Args:
        file_bytes: Raw bytes of a JPEG or PNG image.

    Returns:
        Extracted text string, or _EXTRACTION_FAILED if OCR is unavailable
        or raises an exception.
    """
    if not OCR_AVAILABLE:
        return _EXTRACTION_FAILED
    try:
        image = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(image)
    except Exception:  # noqa: BLE001
        return _EXTRACTION_FAILED


def _extract_pdf_text(file_bytes: bytes) -> str:
    """
    Extract plain text from a PDF using pdfplumber.

    Handles both text-based PDFs and scanned PDFs (with graceful fallback).

    Args:
        file_bytes: Raw bytes of a PDF file.

    Returns:
        Extracted text, or _EXTRACTION_FAILED if extraction fails or yields
        too little content to be useful.
    """
    if not PDF_PLUMBER_AVAILABLE:
        # Fallback: simple regex-based extraction
        return _extract_pdf_text_fallback(file_bytes)
    
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text_chunks = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_chunks.append(page_text)
            
            extracted = "\n".join(text_chunks).strip()
            
            if not extracted or len(extracted) < 20:
                return _EXTRACTION_FAILED
            
            return extracted
    except Exception:  # noqa: BLE001
        return _EXTRACTION_FAILED


def _extract_pdf_text_fallback(file_bytes: bytes) -> str:
    """
    Fallback PDF text extraction using simple regex.

    Used when pdfplumber is not available.

    Args:
        file_bytes: Raw bytes of a PDF file.

    Returns:
        Extracted text, or _EXTRACTION_FAILED if extraction fails.
    """
    try:
        raw = file_bytes.decode("latin-1")
        text_chunks: list[str] = []
        
        # Match parenthesised string literals used in PDF Tj/TJ operators
        paren_strings = re.findall(r"\(([^\\\(\)]{2,})\)", raw)
        for chunk in paren_strings:
            # Keep only printable ASCII
            cleaned = re.sub(r"[^\x20-\x7e\n\r\t]", " ", chunk).strip()
            if len(cleaned) > 2:
                text_chunks.append(cleaned)
        
        extracted = " ".join(text_chunks).strip()
        
        if not extracted or len(extracted) < 20:
            return _EXTRACTION_FAILED
        
        return extracted
    
    except Exception:  # noqa: BLE001
        return _EXTRACTION_FAILED



def _extract_raw_text(file_bytes: bytes, content_type: str) -> str:
    """
    Route file bytes to the appropriate text-extraction method.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        content_type: MIME type string, e.g. "image/jpeg" or "application/pdf".

    Returns:
        Extracted plain text.
    """
    mime = content_type.lower()

    if mime in ("image/jpeg", "image/jpg", "image/png", "image/tiff", "image/bmp"):
        return _ocr_image(file_bytes)

    if mime == "application/pdf":
        return _extract_pdf_text(file_bytes)

    # Fallback: attempt UTF-8 decode for unknown types
    try:
        return file_bytes.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return _EXTRACTION_FAILED


def _run_ner(ner_pipeline: "Pipeline | None", text: str) -> dict[str, list[str]]:
    """
    Run the HuggingFace biomedical NER pipeline on text and group results.

    Consecutive B-/I- tokens of the same entity type are joined into a single
    entity string. Recognised types: DISO (diagnosis), CHEM (medications),
    PROC (procedure).

    Args:
        ner_pipeline: A loaded HuggingFace transformers NER pipeline, or None.
        text: Plain text to analyse.

    Returns:
        Dict with keys "diagnosis", "medications", "procedure" — each a list
        of deduplicated entity strings (title-cased). Returns empty lists if
        the pipeline is None or raises an exception.
    """
    result: dict[str, list[str]] = {
        "diagnosis": [],
        "medications": [],
        "procedure": [],
    }

    if ner_pipeline is None:
        return result

    try:
        entities = ner_pipeline(text)
    except Exception:  # noqa: BLE001
        return result

    # Group consecutive B-/I- tokens of the same base type into full spans.
    current_field: str | None = None
    current_tokens: list[str] = []

    for ent in entities:
        label: str = ent.get("entity", "") or ent.get("entity_group", "")
        word: str = ent.get("word", "")

        # Strip B- / I- prefix to get the base type (e.g. "DISO", "CHEM")
        if "-" in label:
            prefix, base_type = label.split("-", 1)
        else:
            prefix, base_type = "B", label

        field = _LABEL_TO_FIELD.get(base_type)

        if field is None:
            # Unknown entity type — flush any in-progress span
            _flush_span(current_field, current_tokens, result)
            current_field = None
            current_tokens = []
            continue

        if prefix == "B" or field != current_field:
            # Beginning of a new entity span
            _flush_span(current_field, current_tokens, result)
            current_field = field
            # Handle subword tokens (## prefix from WordPiece tokenisation)
            current_tokens = [word.lstrip("#")]
        else:
            # Continuation of current span (I- tag)
            if word.startswith("##"):
                # Subword continuation — attach directly without space
                if current_tokens:
                    current_tokens[-1] = current_tokens[-1] + word.lstrip("#")
                else:
                    current_tokens.append(word.lstrip("#"))
            else:
                current_tokens.append(word)

    _flush_span(current_field, current_tokens, result)  # Flush the final span

    return result


def _extract_patient_info(text: str) -> PatientInfo:
    """
    Extract patient age and gender from free text using heuristic regex patterns.

    Age patterns matched:
        "Age: 45", "Age-45", "45 years old", "45 yrs", "45 year"

    Gender patterns matched:
        "Male", "Female", "Sex: M", "Gender: F", standalone "M" or "F"
        after a label.

    Args:
        text: Plain text from OCR or PDF extraction.

    Returns:
        PatientInfo with age (int or None) and gender (str or None).
        Gender is normalised to lowercase "male", "female", or "other".
    """
    age: int | None = None
    gender: str | None = None

    # --- Age extraction ---
    age_patterns = [
        r"\bage\s*[:\-]?\s*(\d{1,3})\b",              # "Age: 45", "Age-45"
        r"\b(\d{1,3})\s*(?:years?|yrs?)(?:\s*old)?\b", # "45 years old", "45 yrs"
        r"\b(\d{1,3})\s*/\s*(?:M|F|male|female)\b",   # "45/M", "45/F"
    ]
    for pattern in age_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            candidate = int(m.group(1))
            if 0 < candidate < 130:  # Sanity check for realistic ages
                age = candidate
                break

    # --- Gender extraction ---
    gender_patterns = [
        r"\b(?:sex|gender)\s*[:\-]?\s*(male|female|m|f)\b",  # "Sex: M", "Gender: Female"
        r"\b(\d{1,3})\s*/\s*(M|F)\b",                         # "45/M", "62/F"
        r"\b(male|female)\b",                                  # plain "Male" / "Female"
    ]
    for pattern in gender_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            # The gender token is always in the last capturing group
            raw_gender = m.group(m.lastindex).lower()
            if raw_gender in ("m", "male"):
                gender = "male"
            elif raw_gender in ("f", "female"):
                gender = "female"
            else:
                gender = "other"
            break

    return PatientInfo(age=age, gender=gender)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_prescription(
    file_bytes: bytes,
    content_type: str,
    ner_pipeline: "Pipeline | None",
) -> ExtractionResult:
    """
    Parse an uploaded prescription file into structured medical data.

    Pipeline:
    1. Extract raw text from the file (OCR for images, text extraction for PDFs).
    2. Run HuggingFace biomedical NER to identify diagnosis, medications, and
       procedure entities (skipped if ner_pipeline is None).
    3. Apply heuristic regex to extract patient age and gender.

    Args:
        file_bytes: Raw bytes of the uploaded prescription file.
        content_type: MIME type of the file (e.g. "image/jpeg", "application/pdf").
        ner_pipeline: A loaded HuggingFace transformers NER pipeline object, or
            None if the model is unavailable. When None, NER is skipped and
            entity lists are returned empty.

    Returns:
        ExtractionResult containing:
            - diagnosis: list of extracted disorder/diagnosis entities
            - procedure: list of extracted procedure entities
            - medications: list of extracted medication/chemical entities
            - patient: PatientInfo with age and gender if detectable
            - raw_text: the plain text before NER (useful for debugging)
    """
    # Step 1: Extract raw text
    raw_text = _extract_raw_text(file_bytes, content_type)

    # Step 2: If extraction failed, skip NER and patient parsing — there is no
    # meaningful text to analyse. Return an ExtractionResult with empty entity
    # lists so callers can detect the failure via empty lists + the raw_text value.
    if raw_text == _EXTRACTION_FAILED:
        return ExtractionResult(
            diagnosis=[],
            procedure=[],
            medications=[],
            patient=PatientInfo(age=None, gender=None),
            raw_text="Could not extract text from file.",
        )

    # Step 3: Named entity recognition
    ner_results = _run_ner(ner_pipeline, raw_text)

    # Step 4: Patient demographics
    patient_info = _extract_patient_info(raw_text)

    return ExtractionResult(
        diagnosis=ner_results["diagnosis"],
        procedure=ner_results["procedure"],
        medications=ner_results["medications"],
        patient=patient_info,
        raw_text=raw_text,
    )
