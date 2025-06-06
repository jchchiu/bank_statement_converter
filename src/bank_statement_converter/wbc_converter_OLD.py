import os.path
import fitz
from datetime import datetime
from .utils import export_to_csv

# Function to extract text from a rectangular area on a PDF page
def text_from_area(pdf_path: str):
    doc = fitz.open(pdf_path)
    
    text = ''
    
    for page in doc:
        text += page.get_text() + '\n'
        
    return text

def get_transactions(text):
    lines = text.split('\n')

    prev_line = ""
    prev_prev_line = ""
    dates = []
    amounts = []
    transactions = []

    new_datef = "%d-%b-%y"
    date_format = "%d %b %Y"

    for line in lines:
        print(line)
        if "Westpac Business One Plus" in line:
 #           print(line)
            dates.append(datetime.strptime(prev_line, date_format).strftime(new_datef))
        if line[0] == "$" or line[0] == "-":
            amounts.append(line[:-1].replace("$", ""))
            transactions.append(prev_prev_line[:-1] + "" + prev_line[:-1])
        prev_prev_line = prev_line
        prev_line = line
        
    if (len(dates) == len(transactions)) and (len(transactions) == len(amounts)):
        print(f"Number of transactions match: {len(dates)}.)")
    else:
        raise (ValueError(f"Length of transactions does not match: \n Dates: {len(dates)} \n \
                            Transactions: {len(transactions)} \n Amounts: {len(amounts)}"))
        
    
    comb_data = [['Date', 'Amount', 'Transaction Details']]

    for i in range(len(dates)):
        comb_data.append([dates[i], amounts[i], transactions[i]])
        
    return comb_data

def convert_wbc(pdf_path: str):
    data = get_transactions(text_from_area(pdf_path))
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '.csv').replace(' ', '_').replace('/','')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))



