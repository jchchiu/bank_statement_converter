import fitz

# Map keywords for the banks
BANK_KEYWORDS = {
    'cba': ['by logging on to the CommBank App or NetBank.'], # Business Transaction Account ONLY
    'anz': ['WELCOME TO YOUR ANZ ACCOUNT AT A GLANCE '], # BUSINESS ADVANTAGE STATEMENT/ BUSINESS ONLINE SAVER/ BUSINESS EXTRA
    'nab': ['National Australia Bank Limited ABN 12 004 044 937 AFSL and Australian Credit Licence 230686'], # Transaction Account
    'wbc': ['Copyright © 2025 Westpac Banking Corporation'], # Westpac Business One Plus 
    'ben': ['Bendigo and Adelaide Bank Limited ABN 11 068 049 178 AFSL/Australian Credit Licence 237879',
            'Bendigo Business Basic Account'] # Bendigo Business Basic Account
}

def extract_first_page_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    text = page.get_text("text")
    doc.close()
    return text

def detect_bank(pdf_path: str) -> str | None:
    text = extract_first_page_text(pdf_path)
    for bank_key, phrases in BANK_KEYWORDS.items():
        for phrase in phrases:
            if phrase in text:
                return bank_key
    return None