import fitz

# Map keywords for the banks
BANK_KEYWORDS = {
    'cba': ['by logging on to the CommBank App or NetBank.',
            'Business Transaction Account'], # Business Transaction Account
    'anz': ['WELCOME TO YOUR ANZ ACCOUNT AT A GLANCE ',
            'BUSINESS ADVANTAGE STATEMENT',
            'BUSINESS ONLINE SAVER STATEMENT',
            'BUSINESS EXTRA STATEMENT'],
    'nab': ['National Australia Bank Limited ABN 12 004 044 937 AFSL and Australian Credit Licence 230686',
            'Transaction Account',           # Transaction Account
            'BUSINESS EVERYDAY AC',          # Business Everyday Account
            'BUSINESS CHEQUE ACCOUNT'],      # Business Cheque Account
    'wbc': ['ABN 33 007 457 141',
            'Transaction Search',            # Westpac Business One Plus Transaction Search
            'Electronic Statement'],         # Westpac Business One Account
    'ben': ['Bendigo and Adelaide Bank Limited ABN 11 068 049 178 AFSL/Australian Credit Licence 237879',
            'Business Basic Account']        # Bendigo Business Basic Account
}

def extract_first_page_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    text = page.get_text("text")
    doc.close()
    return text

"""
The first phrase in the dictionary is to detect the bank. 
The rest of the phrases are specific to the different statements of the same bank.
Returns the bank_key [0] and bank statement type [1]
"""
def detect_bank(pdf_path: str) -> str | None:
    text = extract_first_page_text(pdf_path)
    bank_info = []
    for bank_key, phrases in BANK_KEYWORDS.items():
        i = 0
        for phrase in phrases:
            # If can't find phrase specific to bank move on to next bank
            if i == 0:
                if phrase in text:
                    bank_info.append(bank_key)
                else:
                    break
            else:
                # Return once specific transaction account is found as banks may have different pdf formats
                if phrase in text:
                    bank_info.append(phrase)
                    return bank_info
            i += 1
    return None