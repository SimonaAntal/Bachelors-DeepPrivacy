import json
import os
import re
from google import genai
from google.genai import types

# Label words that should not be flagged as sensitive
LABEL_KEYWORDS = {
    'nume', 'prenume', 'cnp', 'adresa', 'numar', 'iban',
    'data', 'telefon', 'sex', 'nationalitate', 'localitate',
    'strada', 'oras', 'nr', 'bl', 'sc', 'ap', 'cod postal',
    'name'
}


def is_label(text):
    t = text.strip().lower().rstrip(":").rstrip(".")
    return t in LABEL_KEYWORDS


def is_cnp(text):
    return bool(re.fullmatch(r'\d{13}', text))


def is_iban_ro(text):
    t = text.strip().upper().replace(" ", "")
    return bool(re.fullmatch(r'RO\d{2}[A-Z0-9]{16}', t))

def is_phone_ro(text):
    t = text.strip().replace(" ", "").replace("-", "")
    return bool(re.fullmatch(r'(\+40|0040|0)[0-9]{9}', t))

def is_email(text: str) -> bool:
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', text.strip()))


def rule_classify(text):
    t = text.strip()

    if is_cnp(t) or is_iban_ro(text) or is_email(text) or is_phone_ro(text):
        return "I"
    return None  # needs LLM


def llm_classify(texts):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    texts_json = json.dumps(texts, ensure_ascii=False)

    prompt = f"""
        You are a GDPR personal data classifier for OCR-extracted text from Romanian documents.

        Rules:
        - Classify ONLY the actual VALUE, not field labels.
        - If the text looks like a form field label (e.g. "Nume:", "CNP", "Adresa"), return NON_PERSONAL.
        - Date of birth components — even if split across tokens (e.g. "03", "07", "1983" are all part of a birthdate), return DATE.
        - If the text is a real person's full or partial name, return NAME.
        - If it's an ID number, IBAN, phone, email, serial number, return IDENTIFIER.
        - If it's a real physical address or location, return LOCATION.
        - Otherwise return NON_PERSONAL.

        Input (JSON array of strings):
        {texts_json}

        Return ONLY a JSON array of objects like:
        [{{ "text": "...", "label": "IDENTIFIER" }}]

        No explanations.
        """

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )

    try:
        result = json.loads(response.text.strip())
        return result

    except Exception as e:
        print(f"LLM classification failed: {e}")
        return []


def classify_texts(texts):
    sensitive = set()
    undecided = []

    for text in texts:
        label = rule_classify(text)
        if label is None:
            undecided.append(text)
        elif label != "NON_PERSONAL":
            sensitive.add(text)

    if undecided:
        llm_results = llm_classify(undecided)
        for item in llm_results:
            if item["label"] != "NON_PERSONAL" and is_label(item["text"]) == False:
                sensitive.add(item["text"])

    return list(sensitive)