import fitz
import os.path
from .utils import export_to_csv, is_datetime, reformat_date, csv_rename, check_page_rotation, clean_up_values, remove_annots

"""
Get the opening and closing balances from the first page and prints them
Returns the difference in balances to compare to running amount at the end
"""
def diff_balances(doc):
    
    rect = fitz.Rect(0,10,600,350)
    page = doc[0]
    remove_annots(page)
    text = page.get_text(clip=rect) + "\n"
    lines = text.split('\n')
    
    running_balance = None
    balance_flag = False
    credits = None
    credits_flag = False
    debits = None
    debits_flag = False
    closing_balance = 0
    closing_flag = False
    diff_amount = 0
    
    for line in lines:
        if not line.strip():
            continue
        # Get total credits [0] and debits [1] to compare to running amounts calculated
        # Get difference between opening and closing balance [2], opening balance [3] and closing balance [4]
        if line[:18] == 'Opening balance on':
            balance_flag = True
            continue
        if balance_flag == True:
            running_balance = round(float(line[1:].replace(',', '').strip()), 2)
            print(f"Obtained opening balance: ${running_balance}")
            balance_flag = False
            continue
        if line == 'Deposits & credits':
            credits_flag = True
            continue
        if credits_flag == True:
            credits = round(float(line[1:].replace(',', '').strip()), 2)
            print(f"Obtained total credits: ${credits}")
            credits_flag = False
            continue
        if line == 'Withdrawals & debits':
            debits_flag = True
            continue
        if debits_flag == True:
            debits = -round(float(line[1:].replace(',', '').strip()), 2)
            print(f"Obtained total debits: ${debits}")
            debits_flag = False
            continue
        if line[:18] == 'Closing Balance on':
            closing_flag = True
            continue
        if closing_flag == True:
            closing_balance = round(float(line[1:].replace(',', '').strip()), 2)
            print(f"Obtained closing balance: ${closing_balance}")
            closing_flag = False            
            diff_amount = round(closing_balance - running_balance, 2)
            print(f"Obtained difference between opening and closing balance: ${diff_amount}")
            print(f"-------------------------------------------------")
            break
    
    return (round(credits, 2), round(debits, 2), diff_amount, running_balance, closing_balance)

"""Get the transactions"""
def get_transactions(pdf_path: str):        
    doc = check_page_rotation(pdf_path)
    
    amnt_checks = diff_balances(doc)
    init_credits, init_debits = amnt_checks[0], amnt_checks[1]
    diff_amount, running_balance, closing_balance = amnt_checks[2], amnt_checks[3], amnt_checks[4]
    
    comb_data = [['Date', 'Transaction Details', 'Amount']]
    t_line = 0     
    tot_credit = 0
    tot_debit = 0
    tot_running = 0
              
    for page in doc:
        remove_annots(page)
        # ADAPTED FROM: https://github.com/pymupdf/PyMuPDF/discussions/1842
        paths = page.get_drawings()  # extract page's line art

        # make list of row shading rectangles
        # they must be large enough (width & height) and have a fill color
        grids = [  # subselect shading rectangles
            p for p in paths if p["rect"].width > 80 and p["rect"].height > 20 and p["fill"]
        ]
        # the column coordinates are given ... by someone
        x_values = set([40,96,320,440,510,580])

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
        r = page.search_for("Bendigo and Adelaide Bank Limited ABN 11 068 049 178 AFSL/Australian Credit Licence 237879")[0]  # do not include footer line
        y_values.add(round(r.y0 - 5))  # add top of footer line as y-coord

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
                    else:
                        break
                if j == 1:
                    comb_data[t_line+1].append(text.strip())
                    continue
                if j == 2:
                    if text:
                        amount_str = str(text.replace(',', '').replace('$', '').strip())
                        comb_data[t_line+1].append('-' + amount_str)
                        running_balance -= float(amount_str)
                        tot_running -= float(amount_str)
                        tot_debit -= float(amount_str)
                    continue
                if j == 3:
                    if text:
                        amount_str = str(text.replace(',', '').replace('$', '').strip())
                        comb_data[t_line+1].append(amount_str)
                        running_balance += float(amount_str)
                        tot_running += float(amount_str)
                        tot_credit += float(amount_str)
                    continue
                if j == 4:
                    given_balance = round(float(text.replace(',', '').replace('$', '').strip()), 2)
                    if round(running_balance, 2) == given_balance:
                        continue
                    else:
                        raise (ValueError(f"Running balance and given balance do not match: {running_balance}, {given_balance} \n \
                                    Find at row: {i}"))
                    
            t_line += 1
            
    comb_data_clean = [x for x in comb_data if x != []]
    print(f"Number of transactions: {len(comb_data_clean)}")
    print(f"Calculated total credits: ${round(tot_credit, 2)}")
    print(f"Calculated total debits: ${round(tot_debit, 2)}")
    print(f"Calculated closing balance: ${round(running_balance, 2)}")
    print(f"Calculated difference between opening and closing balance: ${round(tot_running, 2)}")
            
    if (round(tot_running, 2) == diff_amount) and (round(tot_credit, 2) == init_credits) and (round(tot_debit, 2) == init_debits) and \
        (round(running_balance, 2) == round(closing_balance, 2)):
        print('Running balance, closing balance and difference between total credits and total debits same.')
        print(f"-------------------------------------------------")
    else:
        raise (ValueError(f"Running balance and difference between total credits and total debits do not match: {running_balance}, {diff_amount}"))

    return comb_data_clean
            
def convert_ben(pdf_path: str):
    data = get_transactions(pdf_path)
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '.csv')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))
    return csv_rename(pdf_path)
