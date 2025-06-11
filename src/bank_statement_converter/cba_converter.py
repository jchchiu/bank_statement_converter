import os.path
import fitz
from datetime import datetime
from .utils import is_datetime, export_to_csv, csv_rename, remove_annots

# Function to extract text from a rectangular area on a PDF page
def text_from_area(pdf_path: str):
    doc = fitz.open(pdf_path)
    
    text = ''
    rect = fitz.Rect(50,100,600,1200)
    
    for page_number in range(doc.page_count):
        if page_number == 0:
            page = doc[0]
            remove_annots(page)
            rect0 = fitz.Rect(50,500,600,1200)
            text += page.get_text(clip=fitz.Rect(50,500,600,1200)) + "\n"
            continue
        page = doc[page_number]
        remove_annots(page)
        text += page.get_text(clip=rect) + "\n"
        
    return text

# Function to return the range of the years in the statement period
def statement_years(pdf_path: str):
    doc = fitz.open(pdf_path)
    rect = fitz.Rect(300,10,600,350)
    page = doc[0]
    remove_annots(page)
    text = page.get_text(clip=rect) + "\n"
    lines = text.split('\n')
    years = ['2022', '2023', '2024', '2025', '2026', '2027']
    period_flag = False
    period_years = []
    for line in lines:
        if line == 'Period':
            period_flag = True
            continue
        if period_flag:
            for year in years:
                if year in line:
                    period_years.append(year)

    return period_years
    
def get_transactions(pdf_path: str):
    yr_rollover_flag = False
    period_years = statement_years(pdf_path)
    print(f"Number of year in the statement period: {len(period_years)}")
    if len(period_years) == 1:
        year = period_years[0]
    else:
        year = period_years[0]
        yr_rollover_flag = True
        
    text = text_from_area(pdf_path)
    lines = text.split('\n')
    
    # Need this to get amount if line detection puts transaction and amount in same line
    prev_line = ''
    
    # Date format of pdf, and what is needed for QIF format
    date_format = "%d %b %Y"
    new_datef = "%d-%b-%y"
    date_flag = False
    dates = []
    
    transaction = ''
    transactions = []
    
    amounts = []
    
    running_balance = None
    balance_flag = False
    closing_balance = None
    closing_flag = False
    
    for line in lines:
        if not line.strip():
            continue
        
        # Year is not always in the same position with line 'OPENING BALANCE";
        #  start of line could have day and month as well
        if line[-15:] == 'OPENING BALANCE':
            balance_flag = True
            continue
        if balance_flag == True:
            running_balance = round(float(line[1:-2].replace(',', '').strip()), 2)
            print(f"Obtained opening balance: ${running_balance}")
            balance_flag = False
            continue
        
        # To get the closing balance and compare with running amount; if matches break 
        if line[-15:] == 'CLOSING BALANCE':
            closing_flag = True
            continue
        if closing_flag == True:
            closing_balance = round(float(line[1:-2].replace(',', '').strip()), 2)
            print(f"Obtained closing balance: ${closing_balance}")
            print(f"-------------------------------------------------")
            closing_flag = False
            break
        
        # To get transaction names
        if line[0] == '$' and date_flag == True:
            if line == '$':
                amount = prev_line.replace(',', '').strip()
                running_balance -= round(float(amount), 2)
                amounts.append('-' + str(amount))
                transaction = transaction[:-len(prev_line)] # Remove amount from transaction text
            else:
                amount = line[1:].replace(',', '').strip()
                running_balance += round(float(amount), 2)
                amounts.append(str(amount))

            transactions.append(transaction)
            date_flag = False
            transaction = ''
            continue
        
        # To keep adding text of transactions on new lines
        if date_flag == True:
            transaction = transaction + ' ' + line
            prev_line = line
            continue
        
        # Check whether running balance is equal to given line balance
        if line[0] == '$' and line[-3:] == ' CR':
            given_balance = round(float(line[1:-2].replace(',', '').strip()), 2)
            running_balance = round(running_balance, 2)
            if running_balance == given_balance:
                continue
            else:
                raise (ValueError(f"Running balance and given balance do not match: {running_balance}, {given_balance} \n \
                                    Find at line: {line}"))
        
        # Checks the first instance of ' JAN ' and if year rollover flag is raised; if so then update year
        if is_datetime(str(line[:6] + " " + year), date_format) and (line[2:7] == ' Jan ') and yr_rollover_flag:
            year = period_years[1]
            yr_rollover_flag = False
            
        # Checks whether line is a date using datetime function; also adds start of transaction name
        if is_datetime(str(line[:6] + " " + year), date_format):
            dates.append((datetime.strptime((line[:6] + " " + year), date_format).strftime(new_datef)))
            date_flag = True
            transaction = line[7:].strip()
            prev_line = line
            continue
    
    if (len(dates) == len(transactions)) and (len(transactions) == len(amounts)):
        print(f"Number of transactions match: {len(dates)}")
    else:
        raise (ValueError(f"Length of transactions does not match: \n Dates: {len(dates)} \n \
                            Transactions: {len(transactions)} \n Amounts: {len(amounts)}"))
        
    # Combine the data into a single array so it is easier to convert to csv
    if running_balance == closing_balance:
        print('Running balance and closing balance match.')
        print(f"-------------------------------------------------")
        comb_data = [['Date', 'Amount', 'Transaction Details']]
        for i in range(len(dates)):
            comb_data.append([dates[i], amounts[i], transactions[i]])
    else:
        raise (ValueError(f"Running balance and closing balance do not match: {running_balance}, {closing_balance}"))

    return comb_data
        
def convert_cba(pdf_path: str):
    data = get_transactions(pdf_path)
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '.csv')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))
    return csv_rename(pdf_path)