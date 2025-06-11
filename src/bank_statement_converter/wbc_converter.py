import fitz
import os.path
from .utils import export_to_csv, is_datetime, reformat_date, csv_rename, check_page_rotation, clean_up_values, remove_annots

"""Get the transactions"""
def get_transactions(pdf_path: str):        
    doc = check_page_rotation(pdf_path)
    
    comb_data = [['Date', 'Transaction Details', 'Amount']]
    running_amount = 0
    t_line = 0     
              
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
        x_values = set([40,105,215,365,410,500])

        y_values = set()  # these need to be computed now

        for p in grids:  # walk through shading rectangles
            # and add their coordinates to what we have
            r = p["rect"]
            x_values.add(round(r.x0))  # left of shading
            x_values.add(round(r.x1))  # right of shading
            y_values.add(r.y0 + 8)  # top of shading
            y_values.add(r.y1 - 2)  # bottom of shading

        # the page top and bottom needs to be added as y-coordinate as well
        # top transaction otherwise will not be found if first transaction is not shaded
        r = page.search_for("Copyright")[0]  # do not include footer line
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
        for i, row in enumerate(cells[::2]): # Every even transaction from cells correspond to statement
            comb_data.append([])
            for j, cell in enumerate(row):  # extract text of each table cell
                text = page.get_textbox(cell).replace("\n", " ").strip()
                if j == 0:
                    if is_datetime(text, "%d %b %Y"):
                        comb_data[t_line+1].append(reformat_date(text))
                        continue
                    else:
                        break
                if j == 2:
                    comb_data[t_line+1].append(text)
                    continue
                if j == 3:
                    if '-' in text:
                        dollar_idx = text.index("$")
                        amount_str = str(text[dollar_idx:].replace('$', '').strip())
                        comb_data[t_line+1].append('-' + amount_str)
                        running_amount -= float(amount_str)
                        break
                    continue
                if j == 4:
                    if text:
                        dollar_idx = text.index("$")
                        amount_str = str(text[dollar_idx:].replace('$', '').strip())
                        comb_data[t_line+1].append(amount_str)
                        running_amount += float(amount_str)
                        break
                    break
            t_line += 1
            
    comb_data_clean = [x for x in comb_data if x != []]
    print(f"Number of transactions: {len(comb_data_clean)}")
        
    print(f"Running balance: {round(running_amount, 2)}")
    print(f"-------------------------------------------------")
#    if round(running_amount,2) == diff_amount:
#        print('Running balance and difference between opening and closing balance is equal.')
#    else:
#        raise (ValueError(f"Running amount and difference in opening and closing balance do not match: {running_amount}, {diff_amount}"))

    return comb_data_clean
            
def convert_wbc(pdf_path: str):
    data = get_transactions(pdf_path)
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '.csv')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))
    return csv_rename(pdf_path)