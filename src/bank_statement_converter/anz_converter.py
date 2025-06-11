import fitz
import os.path
from .utils import export_to_csv, is_datetime, reformat_date, csv_rename, remove_annots, check_page_rotation

"""
Get the transactions
"""
def get_transactions(pdf_path: str):        
    doc = check_page_rotation(pdf_path)

    comb_data = [['Date', 'Transaction Details', 'Amount']]
    running_balance = 0
    t_line = 0
    years = ['2023', '2024', '2025']
    year = ''
    opening_flag = True
    closing_flag = False
    end_flag = False
              
    for page in doc[1:]:
        remove_annots(page)
        
        # ADAPTED FROM: https://github.com/pymupdf/PyMuPDF/discussions/1842
        paths = page.get_drawings()  # extract page's line art

        # the column coordinates are given ... by someone
        x_values = set([41,75,320,408,500,563])

        y_values = []  # these need to be computed now
        for path in paths:
            for item in path['items']:
                p1 = item[1]
                y_values.append(p1.y)

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

        # Now extract the text of each of the cells
        for i, row in enumerate(cells):
            comb_data.append([])
            for j, cell in enumerate(row):  # extract text of each table cell
                text = page.get_textbox(cell).replace("\n", " ").strip()
                if j == 0:
                    if text[:4] in years:
                        year = text[:4]
                        if not opening_flag: # For the date if on the same line of the year
                            if is_datetime(text[-6:] + ' ' + year, "%d %b %Y"):
                                comb_data[t_line+1].append(reformat_date(text + ' ' + year))
                                continue
                        continue
                    if is_datetime(text + ' ' + year, "%d %b %Y"): # For the year
                        comb_data[t_line+1].append(reformat_date(text + ' ' + year))
                    continue
                
                if j == 1: # For transaction details
                    if text == 'OPENING BALANCE':
                        opening_flag = True
                        continue
                    if text == 'TOTALS AT END OF PAGE':
                        break
                    if text == 'TOTALS AT END OF PERIOD':
                        closing_flag = True
                        continue
                    comb_data[t_line+1].append(text)
                    continue
                
                if j == 2:
                    if 'Withdrawals ($)' in text:
                        continue
                    if text != 'blank':
                        amount_str = str(text.replace(',', '').strip())
                        comb_data[t_line+1].append('-' + amount_str)
                        running_balance -= float(amount_str)
                    continue
                
                if j == 3:
                    if 'Deposits ($)' in text:
                        continue
                    if text != 'blank':
                        amount_str = str(text.replace(',', '').strip())
                        comb_data[t_line+1].append(amount_str)
                        running_balance += float(amount_str)
                    continue
                
                if j == 4:
                    if closing_flag:
                        closing_balance = round(float(text[12:].replace(',', '').replace('$','').strip()), 2)
                        print(f"Obtained closing balance: ${closing_balance}")
                        print(f"-------------------------------------------------")
                        if round(running_balance, 2) == closing_balance:
                            print('Running balance and closing balance match.')
                            print(f"-------------------------------------------------")
                            end_flag = True
                            break
                        else:
                            raise (ValueError(f"Running balance and closing balance do not match: {running_balance}, {closing_balance} \n \
                                        Find at line: {t_line}"))
                    if text[-2:] == 'DR': # If the given balance is negative it has 'DR' suffix
                        given_balance = -round(float(text[:-2].replace(',', '').strip()), 2)  
                    else:                      
                        given_balance = round(float(text.replace(',', '').strip()), 2)
                    if opening_flag:
                        running_balance = given_balance
                        print(f"Obtained opening balance: ${running_balance}")
                        opening_flag = False
                        break
                    if round(running_balance, 2) == given_balance:
                        continue
                    else:
                        raise (ValueError(f"Running balance and given balance do not match: {running_balance}, {given_balance} \n \
                                    Find at line: {t_line}"))
                        
            if end_flag:
                break    
            t_line += 1
        
        if end_flag:
            break
                
    comb_data_clean = [x for x in comb_data if x != []]
    print(f"Number of transactions: {len(comb_data_clean)}")
    
    return comb_data_clean

def convert_anz(pdf_path: str):
    data = get_transactions(pdf_path)
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '.csv')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))
    return csv_rename(pdf_path)