import os.path
import fitz
import pymupdf
from datetime import datetime
from .utils import is_datetime, export_to_csv, csv_rename, remove_annots

# Function to extract text from a rectangular area on a PDF page
def text_from_area(pdf_path: str):
    doc = fitz.open(pdf_path)
    
    text = ''
    rect = fitz.Rect(0,0,600,800)
    
    for page_number in range(doc.page_count):
        page = doc[page_number]
        remove_annots(page)
        text += page.get_text(clip=rect) + "\n"
        
    return text
    
def get_transactions(pdf_path: str):
    text = text_from_area(pdf_path)
    lines = text.split('\n')
    
    # Date format of pdf, and what is needed for QIF format
    date_format = "%d %b %Y"
    new_datef = "%d-%b-%y"
    date_flag = False
    dates = []
    year = ''
    year_flag = False
    first_year_flag = True
    
    transaction = ''
    transactions = []
    
    amounts = []
    
    running_balance = 0
    balance_flag = False
    closing_balance = 0
    closing_flag = False
    
    init_credits = 0
    credits_flag = False
    init_debits = 0
    debits_flag = False
    diff_amount = 0
    tot_credit = 0
    tot_debit = 0
    tot_running = 0
    
    for line in lines:
        if not line.strip():
            continue
        
        # To get the transactions year (NOTE: may be error in future if statement spans 2 years)
        elif line[:4] == 'Date' and first_year_flag:
            year_flag = True
        elif year_flag:
            year = line[-4:]
            year_flag = False
            first_year_flag = False
        
        # Obtain opening figures
        elif line == 'Opening Balance':
            balance_flag = True
        elif balance_flag == True:
            running_balance = round(float(line[1:-2].replace(',', '').strip()), 2)
            print(f"Obtained opening balance: ${running_balance}")
            balance_flag = False
        
        elif line == 'Closing Balance':
            closing_flag = True
        elif closing_flag == True:
            closing_balance = round(float(line[1:-2].replace(',', '').strip()), 2)
            print(f"Obtained closing balance: ${closing_balance}")
            closing_flag = False
        
        elif line == 'Total Credit':
            credits_flag = True
        elif credits_flag == True:
            init_credits = round(float(line[1:].replace(',', '').strip()), 2)
            print(f"Obtained total credits: ${init_credits}")
            credits_flag = False
            
        elif line == 'Total Debit':
            debits_flag = True
        elif debits_flag == True:
            init_debits = -round(float(line[1:].replace(',', '').strip()), 2)
            print(f"Obtained total debits: ${init_debits}")
            print(f"-------------------------------------------------")
            diff_amount = round(init_debits + init_credits, 2)
            debits_flag = False
            
        # To get transaction names
        elif (line[0] == '$' or line[1] == '$') and date_flag == True:
            if line[0] == '$':
                amount = line[1:].replace(',', '').strip()
                running_balance += float(amount)
                tot_credit += float(amount)
                tot_running += float(amount)
                amounts.append(str(amount))
            elif line[1] == '$':
                amount = line[2:].replace(',', '').strip()
                running_balance -= float(amount)
                tot_debit -= float(amount)
                tot_running -= float(amount)
                amounts.append('-' + str(amount))

            transactions.append(transaction.strip())
            date_flag = False
            transaction = ''
        
        # To keep adding text of transactions on new lines
        elif date_flag == True:
            transaction = transaction + ' ' + line
        
        # Check whether running balance is equal to given line balance
        # elif line[0] == '$' and (line[-3:] == ' CR' or line[-3:] == ' DR'):
        #     continue
        #     if line[-3:] == ' CR':
        #         given_balance = round(float(line[1:-2].replace(',', '').strip()), 2)
        #     elif line[-3:] == ' DR':
        #         given_balance = -round(float(line[1:-2].replace(',', '').strip()), 2)
        #     running_balance = round(running_balance, 2)
        #     if running_balance == given_balance:
        #         continue
        #     else:
        #         raise (ValueError(f"Running balance and given balance do not match: {running_balance}, {given_balance} \n \
        #                             Find at line: {line}"))
                    
        # Checks whether line is a date using datetime function; also adds start of transaction name
        elif is_datetime(str(line[:6] + " " + year), date_format):
            dates.append((datetime.strptime((line[:6] + " " + year), date_format).strftime(new_datef)))
            date_flag = True
    
    print(f"Calculated total credits: ${round(tot_credit, 2)}")
    print(f"Calculated total debits: ${round(tot_debit, 2)}")
    print(f"Calculated difference between opening and closing balance: ${round(tot_running, 2)}")
    
    if (round(tot_running, 2) == diff_amount) and (round(tot_credit, 2) == init_credits) and (round(tot_debit, 2) == init_debits):
        print('Running amount and difference between total credits and total debits same.')
    else:
        raise (ValueError(f"Running amount and difference between total credits and total debits do not match: {tot_running}, {diff_amount}"))
    
    if (len(dates) == len(transactions)) and (len(transactions) == len(amounts)):
        print(f"Number of transactions match: {len(dates)}")
    else:
        raise (ValueError(f"Length of transactions does not match: \n Dates: {len(dates)} \n \
                            Transactions: {len(transactions)} \n Amounts: {len(amounts)}"))
        
    # Combine the data into a single array so it is easier to convert to csv
    if round(running_balance, 2) == round(closing_balance, 2):
        print('Running balance and closing balance match.')
        print(f"-------------------------------------------------")
        comb_data = [['Date', 'Amount', 'Transaction Details']]
        for i in range(len(dates)):
            comb_data.append([dates[i], amounts[i], transactions[i]])
    else:
        raise (ValueError(f"Running balance and closing balance do not match: {running_balance}, {closing_balance}"))

    return comb_data
        
def convert_zel(pdf_path: str):
    data = get_transactions(pdf_path)
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '.csv')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))
    return csv_rename(pdf_path)