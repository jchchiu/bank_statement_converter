import csv
import pymupdf
import os.path
from datetime import datetime
import fitz
from .utils import is_datetime
from .utils import export_to_csv

# Function to extract text from a rectangular area on a PDF page
def text_from_area(pdf_path: str, page_number=None):
    doc = fitz.open(pdf_path)
    
    text = ''
    rect = fitz.Rect(0,10,600,740)
    
    for page_number in range(doc.page_count):
        page = doc[page_number]
        text += page.get_text(clip=rect) + "\n"
        
    return text

# Function to check whether something is an amount for lines that combine transaction and amount
def is_amount(line):
    try:
        float(line[1:-2].replace(',', '').strip())
        return True
    except ValueError:
        return False

def get_transactions(text, credit_index):
    lines = text.split('\n')
    
    # Need this to get amount if line detection puts transaction and amount in same line
    prev_line = ''
    
    # Date format of pdf, and what is needed for QIF format
    date_format = "%d %b %y"
    new_datef = "%d-%b-%y"
    date_flag = False
    dates = []
    
    transaction = ''
    transactions = []
    
    amounts = []
    
    balance = None
    balance_flag = False
    skip_flag = False
    closing_balance = None
    closing_flag = False
    diff_amount = 0
    opening_skip = False
    
    for line in lines:
#        print(line)
        if not line.strip():
            continue
        
        # To get the opening balance
        if not(opening_skip):
            if line == 'Opening Balance':
                balance_flag = True
                continue
            if balance_flag == True:
                balance = round(float(line[1:-2].replace(',', '').strip()), 2)
                print(f"Obtained opening balance: ${balance}")
                balance_flag = False
                skip_flag = True
                continue
            if line == 'Closing Balance':
                closing_flag = True
                continue
            if closing_flag == True:
                closing_balance = round(float(line[1:-2].replace(',', '').strip()), 2)
                print(f"Obtained closing balance: ${closing_balance}")
                closing_flag = False
                skip_flag = True
                diff_amount = round(closing_balance - balance, 2)
                continue
            if line == 'Particulars': # Start of statement
                skip_flag = False
                opening_skip = True
                continue
            if skip_flag == True:
                continue
        
        # To get transaction names
        if line[0] == '$' and date_flag == True:
            transactions.append(transaction)
            date_flag = False
            transaction = ''
        if date_flag == True:
            transaction = transaction + '' + line
            prev_line = line
            continue
        
        # CHANGE HERE: BALANCE DIFFERENCE IS NOT ALWAYS EQUAL TO THE TRANSACTION
        # INSTEAD IF FIND THIS THEN CHECK WHERE $ is IN PREVIOUS LINE AS COST SOMETIMES
        if line[0] == '$' and line[-3:] == ' CR':
            if is_amount(prev_line):
                amounts.append('-' + str(prev_line[1:].replace(',', '').strip()))
                continue
            else:
                # NOTE: assumes that only one '$' which is the amount
                amount_index = prev_line.index('$')
                amounts.append('-' + str(prev_line[amount_index + 1:].replace(',', '').strip()))
                transactions[-1] = transactions[-1][:amount_index]
                continue

        if is_datetime(line, date_format):
            dates.append((datetime.strptime(line, date_format).strftime(new_datef)))
            date_flag = True
            continue
        
        prev_line = line
        
    if (len(dates) == len(transactions)) and (len(transactions) == len(amounts)):
        print(f"Number of transactions match ({len(dates)})")
    else:
        raise (ValueError(f"Length of transactions does not match: \n Dates: {len(dates)} \n \
                            Transactions: {len(transactions)} \n Amounts: {len(amounts)}"))

    print([amounts[i] for i in credit_index])
    # Manual changing of debit to credit for now using index input
    for i in credit_index:
        amounts[i] = amounts[i][1:]
    
    print([amounts[i] for i in credit_index])
    
    running_amount = 0
    for amount in amounts:
        running_amount += float(amount)
    
    print(round(running_amount,2), diff_amount)
    # Combine the data into a single array so it is easier to convert to csv
    if round(running_amount,2) == diff_amount:
        print('Balance is equal')
        comb_data = [['Date', 'Amount', 'Transaction Details']]
        for i in range(len(dates)):
            comb_data.append([dates[i], amounts[i], transactions[i]])
    else:
        print([amounts[i] for i in credit_index])
        raise (ValueError(f"Running amount and difference in opening and closing balance do not match: {running_amount}, {diff_amount}"))

    return comb_data
        
def convert_nab(pdf_path: str, credit_indices: list[int]):
    data = get_transactions(text_from_area(pdf_path), credit_indices)
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '_BAS.csv').replace(' ', '_').replace('/','')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))
        
#credits_index = [14,37,39,43,56,89,92,93,94,100,109,121,122,130
#                 ,144,152,171,189,222,225,256,266]

#get_transactions(text_from_area(input_path), credits_index)
