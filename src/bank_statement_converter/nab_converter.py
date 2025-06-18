import fitz
import os.path
from .utils import export_to_csv, is_datetime, reformat_date, csv_rename, check_page_rotation, clean_up_values, remove_annots
import re

"""
Get the total credits/debits and their difference, and opening and closing balances from the first page and prints them
Returns the total credits [0], total debits [1] and their difference [2].
Also returns the opening balance [3] and closing balance [4], mainly for Business Everyday Acc
"""
def diff_balances(doc):
    
    rect = fitz.Rect(0,10,600,740)
    page = doc[0]
    remove_annots(page)
    text = page.get_text(clip=rect) + "\n"
    lines = text.split('\n')
    
    credits = None
    credits_flag = False
    debits = None
    debits_flag = False
    diff_amount = 0
    
    opening_balance = None
    balance_flag = False
    closing_balance = None
    closing_flag = False
    
    for line in lines:

        if not line.strip():
            continue
        if (line == 'Opening Balance') or (line == 'Opening balance'):
            balance_flag = True
            continue
        if balance_flag == True:
            if ('CR' in line) or ('Cr' in line):
                opening_balance = round(float(line.replace(',', '').replace('$', '').replace('CR', '').replace('Cr', '').strip()), 2)
            elif ('DR' in line) or ('Dr' in line):
                opening_balance = -round(float(line.replace(',', '').replace('$', '').replace('DR', '').replace('Dr', '').strip()), 2)
            print(f"Obtained opening balance: ${opening_balance}")
            balance_flag = False
            continue
        if (line == 'Closing Balance') or (line == 'Closing balance'):
            closing_flag = True
            continue
        if closing_flag == True:
            if ('CR' in line) or ('Cr' in line):
                closing_balance = round(float(line.replace(',', '').replace('$', '').replace('CR', '').replace('Cr', '').strip()), 2)
            elif ('DR' in line) or ('Dr' in line):
                closing_balance = -round(float(line.replace(',', '').replace('$', '').replace('DR', '').replace('Dr', '').strip()), 2)
            print(f"Obtained closing balance: ${closing_balance}")
            print(f"-------------------------------------------------")
            break
        # Get total credits [0] and debits [1] and their difference [2] to compare to running amounts calculated
        # Difference between opening and closing balance can be different than running amount
        if (line == 'Total Credits') or (line == 'Total credits'):
            credits_flag = True
            continue
        if credits_flag == True:
            credits = round(float(line[1:].replace(',', '').strip()), 2)
            print(f"Obtained total credits: ${credits}")
            credits_flag = False
            continue
        if (line == 'Total Debits') or (line == 'Total debits'):
            debits_flag = True
            continue
        if debits_flag == True:
            debits = -round(float(line[1:].replace(',', '').strip()), 2)
            print(f"Obtained total debits: ${debits}")
            diff_amount = round(debits + credits, 2)
    
    return (round(credits, 2), round(debits, 2), diff_amount, opening_balance, closing_balance)

"""
Get the transactions for Transaction Account
"""
def get_transactions_acc(pdf_path: str):        
    doc = check_page_rotation(pdf_path)
    
    amnt_checks = diff_balances(doc)
    init_credits, init_debits, diff_amount = amnt_checks[0], amnt_checks[1], amnt_checks[2]
    
    comb_data = [['Date', 'Transaction Details', 'Amount']]
    t_line = 0     
    tot_credit = 0
    tot_debit = 0
    tot_running = 0
              
    for page in doc:
        remove_annots(page)
        # To skip empty pages
        if not page.get_text():
            continue
        
        # ADAPTED FROM: https://github.com/pymupdf/PyMuPDF/discussions/1842
        paths = page.get_drawings()  # extract page's line art

        # make list of row shading rectangles
        # they must be large enough (width & height) and have a fill color
        grids = [  # subselect shading rectangles
            p for p in paths if p["rect"].width > 80 and p["rect"].height > 1 and p["fill"]
        ]
        # the column coordinates are given ... by someone
        x_values = set([20,80,355,405,505])

        y_values = set()  # these need to be computed now

        for p in grids:  # walk through shading rectangles
            # and add their coordinates to what we have
            r = p["rect"]
            x_values.add(round(r.x0))  # left of shading
            x_values.add(round(r.x1))  # right of shading
            y_values.add(round(r.y0))  # top of shading
            y_values.add(round(r.y1))  # bottom of shading

        # the page top and bottom needs to be added as y-coordinate as well
        # top transaction otherwise will not be found if first transaction is not shaded
        r = page.search_for("Important")[0]  # do not include footer line
        r2 = page.search_for("Transaction Details")[0] # do not include header line
        y_values.add(round(r.y0 - 5))  # add top of footer line as y-coord
        y_values.add(round(r2.y0 + 30))  # add top of header line as y-coord

        # x- and y-coordinates are now extracted, do further clean-up
        x_values = sorted(list(x_values))
        x_values = clean_up_values(x_values)
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
        for i, row in enumerate(cells):
            comb_data.append([])
            for j, cell in enumerate(row):  # extract text of each table cell
                text = page.get_textbox(cell).replace("\n", " ").strip()
                if j == 0:
                    if is_datetime(text, "%d %b %y"):
                        comb_data[t_line+1].append(reformat_date(text))
                        continue
                    # If function stops working may be because final row too close to 'Important' line
                    # This statement will include Important and adjust if change footer line as y-coord
                    if is_datetime(text[:9], "%d %b %y") and (text[-9:] == 'Important'):
                        comb_data[t_line+1].append(reformat_date(text[:9]))
                        continue
                    else:
                        break
                if j == 1:
                    if text[-1] == '$':
                        text = text[:-1].strip()
                    comb_data[t_line+1].append(text)
                    continue
                if j == 2:
                    if text:
                        amount_str = str(text.replace(',', '').replace('$', '').strip())
                        comb_data[t_line+1].append('-' + amount_str)
                        tot_running -= float(amount_str)
                        tot_debit -= float(amount_str)
                        break
                    continue
                if j == 3:
                    if text:
                        amount_str = str(text.replace(',', '').replace('$', '').strip())
                        comb_data[t_line+1].append(amount_str)
                        tot_running += float(amount_str)
                        tot_credit += float(amount_str)
                        break
                    break
            t_line += 1
            
    comb_data_clean = [x for x in comb_data if x != []]
    print(f"Number of transactions: {len(comb_data_clean) - 1}")
    print(f"Calculated total credits: ${round(tot_credit, 2)}")
    print(f"Calculated total debits: ${round(tot_debit, 2)}")
    print(f"Calculated difference between opening and closing balance: ${round(tot_running, 2)}")
                
    if (round(tot_running, 2) == diff_amount) and (round(tot_credit, 2) == init_credits) and (round(tot_debit, 2) == init_debits):
        print('Running amount and difference between total credits and total debits same.')
        print(f"-------------------------------------------------")
    else:
        raise (ValueError(f"Running amount and difference between total credits and total debits do not match: {tot_running}, {diff_amount}"))

    return comb_data_clean

"""
Function to remove leading and trailing dots (For Business Everyday Account)
"""
def remove_dots(text):
    """Removes leading and trailing dots with spaces."""
    return re.sub(r"^[.\s]+|[.\s]+$", "", text)

"""
Get the transactions for Business Everyday Account
"""
def get_business_everyday(pdf_path: str):        
    doc = check_page_rotation(pdf_path)
    
    amnt_checks = diff_balances(doc)
    init_credits, init_debits, diff_amount = amnt_checks[0], amnt_checks[1], amnt_checks[2]
    
    comb_data = [['Date', 'Transaction Details', 'Amount']]
    running_balance = amnt_checks[3]
    t_line = 0     
    tot_credit = 0
    tot_debit = 0
    tot_running = 0
    balance_flag = False

    for page in doc:
        remove_annots(page)
        
        # To skip empty pages
        if not page.get_text():
            continue
        
        text_wanted = ".........."
        text_instances = page.search_for(text_wanted)
        y_values = []
        
        for found in text_instances:
            y_values.append(found.y1)
            
        # the page top needs to be added as y-coordinate as well
        r2 = page.search_for("Transaction Details")[0] # do not include header line
        y_values.append(round(r2.y0 + 40))  # add top of header line as y-coord

        x_values = [30,97,320,410,480,580]
        # x- and y-coordinates are now extracted, do further clean-up
        x_values = sorted(list(x_values))
        x_values = clean_up_values(x_values)
        y_values = sorted(list(set(y_values)))

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
        for i, row in enumerate(cells):
            comb_data.append([])
            for j, cell in enumerate(row):  # extract text of each table cell
                text = remove_dots(page.get_textbox(cell).replace("\n", " ").strip())
                if j == 0:
                    if text[:4] == 'Date':
                        balance_flag = True
                        continue
                    if is_datetime(text, "%d %b %Y"):
                        current_date = text
                        comb_data[t_line+1].append(reformat_date(current_date))
                    elif not text:
                        comb_data[t_line+1].append(reformat_date(current_date))
                    continue
                if j == 1:
                    if balance_flag == True:
                        continue
                    comb_data[t_line+1].append(text)
                    continue
                if j == 2:
                    if balance_flag == True:
                        continue
                    if text:
                        amount_str = str(text.replace(',', '').strip())
                        comb_data[t_line+1].append('-' + amount_str)
                        running_balance -= float(amount_str)
                        tot_running -= float(amount_str)
                        tot_debit -= float(amount_str)
                    continue
                if j == 3:
                    if balance_flag == True:
                        continue                    
                    if text:
                        amount_str = str(text.replace(',', '').strip())
                        comb_data[t_line+1].append(amount_str)
                        running_balance += float(amount_str)
                        tot_running += float(amount_str)
                        tot_credit += float(amount_str)
                    continue
                if j == 4:
                    if balance_flag == True:
                        given_balance = round(float(text.replace('Balance','').replace('Cr','').replace(',', '').strip()), 2)
                        if round(running_balance, 2) == given_balance:
                            balance_flag = False
                        else:
                            raise (ValueError(f"Running balance and given balance do not match: {running_balance}, {given_balance} \n \
                                        Find at row: {i}"))
                    elif text:
                        given_balance = round(float(text.replace('Cr','').replace(',', '').strip()), 2)
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
            
    if (round(tot_running, 2) == diff_amount) and (round(tot_credit, 2) == init_credits) and (round(tot_debit, 2) == init_debits):
        print('Running amount and difference between total credits and total debits same.')
        print(f"-------------------------------------------------")
    else:
        raise (ValueError(f"Running amount and difference between total credits and total debits do not match: {tot_running}, {diff_amount}"))

    return comb_data_clean
            
"""
Convert NAB pdf depending on statement type
"""
def convert_nab(pdf_path: str, account_type: str):
    if account_type == 'Transaction Account':
        data = get_transactions_acc(pdf_path)
    if account_type == 'BUSINESS EVERYDAY AC':
        data = get_business_everyday(pdf_path)
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '.csv')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))
    return csv_rename(pdf_path)
