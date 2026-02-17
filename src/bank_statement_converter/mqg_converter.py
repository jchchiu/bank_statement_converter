import fitz
import os.path
from .utils import export_to_csv, is_datetime, reformat_date, csv_rename, remove_annots, \
    check_page_rotation, clean_up_values

"""
Get the total credits/debits and their difference, and opening and closing balances from the first page and prints them
Returns the total credits [0], total debits [1] and their difference [2].
Also returns the opening balance [3] and closing balance [4]
"""
def diff_balances(doc):
    
    rect = fitz.Rect(0, 350, 570, 800)
    page = doc[0]
    remove_annots(page)
    text = page.get_text(clip=rect) + "\n"
    lines = text.split('\n')
    
    credits = None
    debits = None
    diff_amount = 0
    
    balance_flag = False
    opening_balance = 0
    closing_balance = None
    
    i = 0
    
    for line in lines:
        if not line.strip():
            continue
        elif (line == '= Closing balance'):
            balance_flag = True
        elif balance_flag and (i == 0):
            if ('CR' in line) or ('Cr' in line):
                opening_balance = round(float(line.replace(',', '').replace('$', '').replace('CR', '').replace('Cr', '').strip()), 2)
            elif ('DR' in line) or ('Dr' in line):
                opening_balance = -round(float(line.replace(',', '').replace('$', '').replace('DR', '').replace('Dr', '').strip()), 2)
            print(f"Obtained opening balance: ${opening_balance}")
            i += 1
        # Get total credits [0] and debits [1] and their difference [2] to compare to running amounts calculated
        elif balance_flag and (i == 1):
            debits = -round(float(line[1:].replace(',', '').strip()), 2)
            print(f"Obtained total debits: ${debits}")
            i += 1
        elif balance_flag and (i == 2):
            credits = round(float(line[1:].replace(',', '').strip()), 2)
            print(f"Obtained total credits: ${credits}")
            diff_amount = round(debits + credits, 2)
            i += 1
        # Get closing balance
        elif balance_flag and (i == 3):
            if ('CR' in line) or ('Cr' in line):
                closing_balance = round(float(line.replace(',', '').replace('$', '').replace('CR', '').replace('Cr', '').strip()), 2)
            elif ('DR' in line) or ('Dr' in line):
                closing_balance = -round(float(line.replace(',', '').replace('$', '').replace('DR', '').replace('Dr', '').strip()), 2)
            print(f"Obtained closing balance: ${closing_balance}")
            print(f"-------------------------------------------------")
            break
    
    return (round(credits, 2), round(debits, 2), diff_amount, opening_balance, closing_balance)

"""
Get the transactions
"""
def get_transactions(pdf_path: str):        
    doc = check_page_rotation(pdf_path)

    amnt_checks = diff_balances(doc)
    init_credits, init_debits, diff_amount = amnt_checks[0], amnt_checks[1], amnt_checks[2]
    
    comb_data = [['Date', 'Transaction Details', 'Amount']]
    running_balance = amnt_checks[3]
    closing_balance = amnt_checks[4]
    t_line = 0     
    tot_credit = 0
    tot_debit = 0
    tot_running = 0
    
    year = '0'
              
    for page in doc[1:]:
        remove_annots(page)
        # To skip empty pages
        if not page.get_text():
            continue
        if not page.get_drawings():
            continue
        
        paths = page.get_drawings()  # extract page's line art
        
        # make list of row shading rectangles
        # they must be large enough (width & height) and have a fill color
        grids = [  # subselect shading rectangles
            p for p in paths if p["rect"].width > 58
        ]
        # the column coordinates are given
        x_values = set([20,80,200,380,440,500,570])

        y_values = set()  # these need to be computed now

        for p in grids:  # walk through shading rectangles
            # and add their coordinates to what we have
            r = p["rect"]
            y_values.add(r.y0)  # top of shading
            y_values.add(r.y1)  # bottom of shading

        # the page bottom needs to be added as y-coordinate as well
        y_values.add(800)

        # x- and y-coordinates are now extracted, do further clean-up
        x_values = sorted(list(x_values))
        y_values = sorted(list(y_values))
        y_values = clean_up_values(y_values)

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
            
        # Now extract the text of each of the cells
        transaction = ''
        for i, row in enumerate(cells):
            comb_data.append([])
            for j, cell in enumerate(row):  # extract text of each table cell
                text = page.get_textbox(cell).replace("\n", " ").strip()
                if j == 0:
                    if is_datetime(text, "%b %Y"):
                        year = text[-4:]
                        break               
                    elif is_datetime(str(text + " " + year), "%b %d %Y"):
                        current_date = str(text + " " + year)
                        comb_data[t_line+1].append(reformat_date(current_date))
                    else:
                        break
                elif j == 1:
                    transaction = transaction + text
                elif j == 2:
                    transaction = transaction + " " + text
                    comb_data[t_line+1].append(transaction.strip())
                    transaction = ''
                elif j == 3:
                    if text:
                        amount_str = str(text.replace(',', '').strip())
                        comb_data[t_line+1].append('-' + amount_str)
                        running_balance -= float(amount_str)
                        tot_running -= float(amount_str)
                        tot_debit -= float(amount_str)
                elif j == 4:
                    if text:
                        amount_str = str(text.replace(',', '').strip())
                        comb_data[t_line+1].append(amount_str)
                        running_balance += float(amount_str)
                        tot_running += float(amount_str)
                        tot_credit += float(amount_str)
                elif j == 5:
                    if text[-2:] == 'CR':
                        given_balance = round(float(text.replace('CR','').replace(',', '').strip()), 2)
                        if round(running_balance, 2) == given_balance:
                            continue
                        else:
                            raise (ValueError(f"Running balance and given balance do not match: {running_balance}, {given_balance} \n \
                                        Find at row: {i}"))
                    elif text[-2:] == 'DR':
                        given_balance = -round(float(text.replace('DR','').replace(',', '').strip()), 2)
                        if round(running_balance, 2) == given_balance:
                            continue
                        else:
                            raise (ValueError(f"Running balance and given balance do not match: {running_balance}, {given_balance} \n \
                                        Find at row: {i}"))                                                                            
            t_line += 1
            
    comb_data_clean = [x for x in comb_data if x != []]
    print(f"Number of transactions: {len(comb_data_clean) - 1}")
    print(f"Calculated total credits: ${round(tot_credit, 2)}")
    print(f"Calculated total debits: ${round(tot_debit, 2)}")
    print(f"Calculated closing balance: ${round(running_balance, 2)}")
    print(f"Calculated difference between opening and closing balance: ${round(tot_running, 2)}")
    
    if (round(running_balance, 2) == closing_balance):
        print('Running closing balance matches given closing balance.')
    else:
        raise (ValueError(f"Running closing balance and given closing balance do not match: {running_balance}, {closing_balance}"))
            
    if (round(tot_running, 2) == diff_amount) and (round(tot_credit, 2) == init_credits) and (round(tot_debit, 2) == init_debits):
        print('Running amount and difference between total credits and total debits same.')
        print(f"-------------------------------------------------")
    else:
        raise (ValueError(f"Running amount and difference between total credits and total debits do not match: {tot_running}, {diff_amount}"))

    return comb_data_clean

def convert_mqg(pdf_path: str):
    data = get_transactions(pdf_path)
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '.csv')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))
    return csv_rename(pdf_path)
