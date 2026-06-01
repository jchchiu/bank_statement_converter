import os.path
import fitz
from datetime import datetime
from .utils import is_datetime, export_to_csv, csv_rename, remove_annots, check_page_rotation, reformat_date

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
    
    running_balance = 0
    balance_flag = False
    closing_balance = 0
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
            if line == 'Nil':
                print(f"Obtained opening balance: ${running_balance}")
                balance_flag = False
                continue
            running_balance = round(float(line[1:-2].replace(',', '').strip()), 2)
            print(f"Obtained opening balance: ${running_balance}")
            balance_flag = False
            continue
        
        # To get the closing balance and compare with running amount; if matches break 
        if line[-15:] == 'CLOSING BALANCE':
            closing_flag = True
            continue
        if closing_flag == True:
            if line == 'Nil':
                print(f"Obtained closing balance: ${closing_balance}")
                print(f"-------------------------------------------------")
                closing_flag = False
                break
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

            transactions.append(transaction.strip())
            date_flag = False
            transaction = ''
            continue
        
        # To keep adding text of transactions on new lines
        if date_flag == True:
            if line == 'DEBIT INTEREST CHARGED on this account':
                date_flag = False
                transaction = ''
                dates.pop()
                continue
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
    if round(running_balance, 2) == round(closing_balance, 2):
        print('Running balance and closing balance match.')
        print(f"-------------------------------------------------")
        comb_data = [['Date', 'Amount', 'Transaction Details']]
        for i in range(len(dates)):
            comb_data.append([dates[i], amounts[i], transactions[i]])
    else:
        raise (ValueError(f"Running balance and closing balance do not match: {running_balance}, {closing_balance}"))

    return comb_data

def get_transactions_backup(pdf_path: str):
    yr_rollover_flag = False
    period_years = statement_years(pdf_path)
    print(f"Number of year in the statement period: {len(period_years)}")
    if len(period_years) == 1:
        year = period_years[0]
    else:
        year = period_years[0]
        yr_rollover_flag = True
        
    # Date format of pdf, and what is needed for QIF format
    date_format = "%d %b %Y"
    
    doc = check_page_rotation(pdf_path)
    
    comb_data = [['Date', 'Transaction Details', 'Amount']]
    t_line = 0     
    tot_running = 0
    
    running_balance = 0
    balance_flag = False
    closing_balance = 0
    closing_flag = False
    
    for page in doc:
        remove_annots(page)
        # To skip empty pages
        if not page.get_text():
            continue
        if not page.get_drawings():
            continue
        
        # ADAPTED FROM: https://github.com/pymupdf/PyMuPDF/discussions/1842
        paths = page.get_drawings()  # extract page's line art
        
        # the column coordinates are given ... by someone
        x_values = set([41,88,320,408,480,563])

        y_values_all = []  # these need to be computed now
        for path in paths:
            for item in path['items']:
                p1 = item[1]
                y_values_all.append(p1.y)
                
        # Find the Y coord of header and remove anything less than
        y_min = page.search_for("Date Transaction")[0].y1
        y_values_all.append(y_min)
        
        try:
            y_closing = page.search_for("CLOSING BALANCE")[0].y1
            y_values_all.append(y_closing)
        except:
            pass
            
        y_values = [y for y  in y_values_all if y >= y_min]

        # x- and y-coordinates are now extracted, do further clean-up
        x_values = sorted(list(x_values))
        y_values = sorted(list(y_values))

        cells = []  # will be container for table cells
                                                                  
        # Create all table cells as PyMuPDF rectangles.
        # The cells of each row form a sublist.
        # So each table cell can be addressed as "cells[i][j]" via its row / col.
        for i in range(len(y_values) - 1):
            row = []
            for j in range(len(x_values) - 1):
                cell = fitz.Rect(x_values[j], y_values[i], x_values[j + 1], y_values[i + 1])
                row.append(cell)
            cells.append(row)

        # # the page top and bottom needs to be added as y-coordinate as well
        # # top transaction otherwise will not be found if first transaction is not shaded
        # r = page.search_for("Date Transaction")[0]  # get header line
        # y_values.add(r.y0)  # add top of footer line as y-coord

        # Now extract the text of each of the cells
        for i, row in enumerate(cells):
            comb_data.append([])
            for j, cell in enumerate(row):  # extract text of each table cell
                text = page.get_textbox(cell).replace("\n", " ").strip()
                if j == 0:
                    if not text:
                        break
                    # Checks the first instance of ' JAN ' and if year rollover flag is raised; if so then update year
                    if is_datetime(str(text[:6] + " " + year), date_format) and (text[2:7] == ' Jan ') and yr_rollover_flag:
                        year = period_years[1]
                        yr_rollover_flag = False    
                    # Checks whether line is a date using datetime function; also adds start of transaction name
                    if is_datetime(str(text[:6] + " " + year), date_format):
                        comb_data[t_line+1].append(reformat_date(str(text[:6] + " " + year)))
                    else:
                        break
                elif j == 1:
                    if text[-15:] == 'OPENING BALANCE':
                        balance_flag = True
                        comb_data[t_line+1].pop()
                    elif text[-15:] == 'CLOSING BALANCE':
                        closing_flag = True
                        comb_data[t_line+1].pop()
                    else:
                        comb_data[t_line+1].append(text)
                elif j == 2:
                    if text:
                        amount_str = str(text.replace(',', '').strip())
                        comb_data[t_line+1].append('-' + amount_str)
                        running_balance -= float(amount_str)
                        tot_running -= float(amount_str)
                elif j == 3:
                    if text:
                        amount_str = str(text.replace(',', '').strip())
                        comb_data[t_line+1].append(amount_str)
                        running_balance += float(amount_str)
                        tot_running += float(amount_str)
                elif j == 4:
                    if balance_flag == True:
                        if text[-2:] == 'CR':
                            opening_balance = round(float(text[:-2].replace(',', '').strip()), 2)
                            running_balance = round(float(text[:-2].replace(',', '').strip()), 2)
                        elif text[-2:] == 'DR':
                            opening_balance = -round(float(text[:-2].replace(',', '').strip()), 2)
                            running_balance = -round(float(text[:-2].replace(',', '').strip()), 2)
                        else:
                            raise(ValueError("Can't get opening balance"))
                        print(f"Obtained opening balance: ${round(opening_balance, 2)}")
                        balance_flag = False
                        continue
                    
                    if closing_flag == True:
                        if text[-2:] == 'CR':
                            closing_balance = round(float(text[:-2].replace(',', '').strip()), 2)
                        elif text[-2:] == 'DR':
                            closing_balance = -round(float(text[:-2].replace(',', '').strip()), 2)
                        else:
                            raise(ValueError("Can't get opening balance"))
                        print(f"Obtained closing balance: ${round(closing_balance, 2)}")
                        diff_amount = round(closing_balance - opening_balance, 2)
                        print(f"Obtained difference between opening and closing balance: ${diff_amount}")
                        print(f"-------------------------------------------------")
                        break
                    
                    if text[-2:] == 'CR':
                        given_balance = round(float(text[:-2].replace(',', '').strip()), 2)
                    elif text[-2:] == 'DR':
                        given_balance = -round(float(text[:-2].replace(',', '').strip()), 2)
                    else:
                        raise(ValueError("Can't get given balance"))

                    if round(running_balance, 2) == given_balance:
                        continue
                    else:
                        raise (ValueError(f"Running balance and given balance do not match: {running_balance}, {given_balance} \n \
                                    Find at row: {i}"))
            
            if closing_flag:
                break
            
            t_line += 1
            
        if closing_flag:
            break
        
    comb_data_clean = [x for x in comb_data if x != []]
    print(f"Number of transactions: {len(comb_data_clean) - 1}")
    print(f"Calculated closing balance: ${round(running_balance, 2)}")
    print(f"Calculated difference between opening and closing balance: ${round(tot_running, 2)}")
            
    if (round(tot_running, 2) == diff_amount) and (round(running_balance, 2) == round(closing_balance, 2)):
        print('Running balance, closing balance and difference between total credits and total debits same.')
        print(f"-------------------------------------------------")
    else:
        raise (ValueError(f"Running balance and difference between total credits and total debits do not match: {running_balance}, {diff_amount}"))

    return comb_data_clean
        
def convert_cba(pdf_path: str):
    try:
        data = get_transactions(pdf_path)
    except ValueError:
        print('Conversion failed. Switching to backup converter, this may take a while.')
        print(f"-------------------------------------------------")
        try:
            data = get_transactions_backup(pdf_path)
        except ValueError:
            raise (ValueError('Backup conversion failed'))
        
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '.csv')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))
    return csv_rename(pdf_path)