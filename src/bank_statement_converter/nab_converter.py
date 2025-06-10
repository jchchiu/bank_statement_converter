import fitz
import os.path
from .utils import export_to_csv, is_datetime, reformat_date, csv_rename

def clean_up_values(values):
    """This removes drawings artifact coordinates.

    Can be given a sorted list of floats. Will remove the larger one of any
    two in sequence if it is closer than 3 to its predecessor.
    """
    for i in range(len(values) - 1, -1, -1):
        if i == 0:  # reached start of list
            continue
        if values[i] - values[i - 1] <= 8:  # too close: remove larger one
            values.pop(i)
    return values

"""
Read original file and process page 0. If rotated, make an intermediate,
unrotated page first to ease processing it
"""
def check_page_rotation(pdf_path: str):
    src = fitz.open(pdf_path)  # original file
    spage = src[0]
    spage.clean_contents()  # make sure we have a clean PDF page source
    rotation = spage.rotation  # check page rotation
    if rotation != 0:
        w, h = spage.rect.width, spage.rect.height
        spage.set_rotation(0)  # set rotation to 0
        doc = fitz.open()  # make intermediate PDF
        page = doc.new_page(width=w, height=h)  # give a new page
        # copy old page into it, reverting its rotation
        page.show_pdf_page(page.rect, src, 0, rotate=-rotation)
    else:  # not rotated
        doc = src
    return doc

"""
Get the opening and closing balances from the first page and prints them
Returns the difference in balances to compare to running amount at the end
"""
def diff_balances(doc):
    
    rect = fitz.Rect(0,10,600,740)
    page = doc[0]
    text = page.get_text(clip=rect) + "\n"
    lines = text.split('\n')
    
    credits = None
    credits_flag = False
    debits = None
    debits_flag = False
    diff_amount = 0
    
    for line in lines:

        if not line.strip():
            continue
        # Get total credits [0] and debits [1] and their difference [2] to compare to running amounts calculated
        # Difference between opening and closing balance can be different than running amount
        if line == 'Total Credits':
            credits_flag = True
            continue
        if credits_flag == True:
            credits = round(float(line[1:].replace(',', '').strip()), 2)
            print(f"Obtained total credits: ${credits}")
            credits_flag = False
            continue
        if line == 'Total Debits':
            debits_flag = True
            continue
        if debits_flag == True:
            debits = -round(float(line[1:].replace(',', '').strip()), 2)
            print(f"Obtained total debits: ${debits}")
            print(f"-------------------------------------------------")
            diff_amount = round(debits + credits, 2)
            break
    
    return (round(credits, 2), round(debits, 2), diff_amount)

"""Get the transactions"""
def get_transactions(pdf_path: str):        
    doc = check_page_rotation(pdf_path)
    
    amnt_checks = diff_balances(doc)
    init_credits, init_debits, diff_amount = amnt_checks[0], amnt_checks[1], amnt_checks[2]
    
    comb_data = [['Date', 'Transaction Details', 'Amount']]
    running_amount = 0
    t_line = 0     
    tot_credit = 0
    tot_debit = 0
              
    for page in doc:
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
                        running_amount -= float(amount_str)
                        tot_debit -= float(amount_str)
                        break
                    continue
                if j == 3:
                    if text:
                        amount_str = str(text.replace(',', '').replace('$', '').strip())
                        comb_data[t_line+1].append(amount_str)
                        running_amount += float(amount_str)
                        tot_credit += float(amount_str)
                        break
                    break
            t_line += 1
            
    comb_data_clean = [x for x in comb_data if x != []]
    print(f"Number of transactions: {len(comb_data_clean)}")
            
    if (round(running_amount, 2) == diff_amount) and (round(tot_credit, 2) == init_credits) and (round(tot_debit, 2) == init_debits):
        print('Running balance and difference between total credits and total debits same.')
        print(f"-------------------------------------------------")
    else:
        raise (ValueError(f"Running balance and difference between total credits and total debits do not match: {running_amount}, {diff_amount}"))

    return comb_data_clean
            
def convert_nab(pdf_path: str):
    data = get_transactions(pdf_path)
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '.csv')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))
    return csv_rename(pdf_path)
