import fitz
import os.path
from .utils import export_to_csv, is_datetime, reformat_date, csv_rename, remove_annots, \
    check_page_rotation, clean_up_values

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
        # the column coordinates are given ... by someone
        x_values = set([20,80,200,370,440,500,570])

        y_values = set()  # these need to be computed now

        for p in grids:  # walk through shading rectangles
            # and add their coordinates to what we have
            r = p["rect"]
            y_values.add(r.y0)  # top of shading
            y_values.add(r.y1)  # bottom of shading

        # the page top and bottom needs to be added as y-coordinate as well
        # top transaction otherwise will not be found if first transaction is not shaded
        try:
            r = page.search_for("Closing balance")[1]  # Find footer line (Use second in list as search_for is not case sensitive)
            y_values.add(r.y0 - 2) # add top of footer line
            y_values.add(r.y1 + 2)# add bottom of footer line as y-coord
        except:
            y_values.add(800) # Add line just above "Statement No." at the bottom of the page just in case no CLOSING BALANCE
        #y_values.add(r2.y0)  # add top of header line as y-coord

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


def convert_mqg(pdf_path: str):
    data = get_transactions(pdf_path)
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '.csv')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))
    return csv_rename(pdf_path)

if __name__ == '__main__':
    main()