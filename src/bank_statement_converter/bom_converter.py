import os.path
import fitz
from datetime import datetime
from .utils import is_datetime, export_to_csv, csv_rename, remove_annots, check_page_rotation, reformat_date
import re
from collections import defaultdict

"""
Get the range of the years in the statement period
"""
def statement_years(doc):
    page = doc[0]
    remove_annots(page)
    years = page.search_for("Statement Period")
    # Get rectangle of right of statement period as well as its y0, y1 coordinates
    rect = fitz.Rect(years[0].x1,years[0].y0,600,years[0].y1)
    text = page.get_text(clip=rect) + "\n"
    lines = text.split('\n')
    period_years = []

    for line in lines:
        if is_datetime(line[:10], "%d/%m/%Y"):
            period_years.append(line[6:10])
        if is_datetime(line[-10:], "%d/%m/%Y"):
            period_years.append(line[-4:])

    return list(set(period_years))

"""
Get the total credits/debits and their difference, and opening and closing balances from the first page and prints them
Returns the total credits [0], total debits [1] and their difference [2].
Also returns the opening balance [3] and closing balance [4]
"""
def get_balances(page):
    remove_annots(page)
    y_top = page.search_for("Opening Balance")
    y_bot = page.search_for("Transaction Details")
    rect = fitz.Rect(0, (y_top[0].y1 + 1), 600, (y_bot[0].y0 - 1))

    text = page.get_text(clip=rect) + "\n"
    lines = text.split('\n')
    
    credits = 0
    debits = 0
    diff_amount = 0
    
    opening_balance = 0
    closing_balance = 0
    
    i = 0
    
    for line in lines:
        if i == 0:
            opening_balance = round(float(line.replace(',', '').strip()), 2)
            print(f"-------------------------------------------------")
            print(f"Obtained initial opening balance: ${opening_balance}")
        elif i == 2:
            credits = round(float(line.replace(',', '').strip()), 2)
            print(f"Obtained total credits: ${credits}")
        elif i == 4:
            debits = -round(float(line.replace(',', '').strip()), 2)
            print(f"Obtained total debits: ${debits}")
            diff_amount = round(debits + credits, 2)
        elif i == 6:
            closing_balance = round(float(line.replace(',', '').strip()), 2)
            print(f"Obtained initial opening balance: ${closing_balance}")
            print(f"-------------------------------------------------")
            break
        i += 1
    
    return (round(credits, 2), round(debits, 2), diff_amount, opening_balance, closing_balance)

"""
Get x-values for BOM transactions account dynamically except for middle
"""
def get_x_coords(page):
    remove_annots(page)
    x_coords = []

    # Find the top Y coord
    y_0 = page.search_for("Transaction Details")[0].y0
    
    # Set the cropbox based on y-coords
    page.set_cropbox(fitz.Rect(0.0,y_0,595.0,840))
    
    # Search for left of text as column delineator
    # Left of Date
    x_coords.append(page.search_for("Date")[0].x0)
    # Left of Transaction Description
    x_coords.append(page.search_for("Transaction Description")[0].x0 - 1)
    # Set Column b/t Transaction Description and Debit manually (300.0)
    x_coords.append(312.0)
    # Right of Debit
    x_coords.append(page.search_for("Debit")[0].x1 + 1)
    # Not getting credit properly for some reason, manually set
    x_coords.append(460.0)
    # Right of Balance $
    x_coords.append(page.search_for("Balance $")[0].x1 + 10)
    
    # revert CropBox change
    page.set_cropbox(page.mediabox)
    
    return sorted(x_coords)

"""
Get y row coordinates using Date column, as well as phrase at bottom of page
"""

DATE_RE = re.compile(
    r"^\d{1,2}\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)$",
    re.I
)

TERMINATORS = [
    "SUB TOTAL CARRIED FORWARD TO NEXT PAGE",
    "CLOSING BALANCE",
]

def find_terminator_y(page, terminators):
    for terminator in terminators:
        y0 = find_text_y(page, terminator)

        if y0 is not None:
            return y0

    return None

def get_table_row_ys(page):
    date_x0 = page.search_for("Date")
    trans_x1 = page.search_for("Transaction Description")
    
    terminator_y = find_terminator_y(page, TERMINATORS)

    if terminator_y is None:
        raise ValueError(print("WARNING: table terminator not found"))
        
    left_x0, right_x1 = date_x0[0].x0, trans_x1[0].x0
    top_y0, bot_y = date_x0[0].y1, terminator_y
    rect = fitz.Rect(left_x0, top_y0, right_x1, bot_y)
    
    words = page.get_text("words", clip=rect)

    # Group words into lines
    lines = defaultdict(list)

    for word in words:
        x0, y0, x1, y1, text, block_no, line_no, word_no = word
        lines[(block_no, line_no)].append(word)

    row_y0s = []
    i = 0
    for line_words in lines.values():
        line_words.sort(key=lambda w: w[0])

        text = " ".join(w[4] for w in line_words)
        
        if DATE_RE.match(text):
            # For the first line to ignore the "SUB TOTAL CARRIED FORWARD FROM PREVIOUS PAGE"
            if i == 0:
                y0 = min(w[1] for w in line_words) + 3
                row_y0s.append(y0)
                i += 1
                continue
            y0 = min(w[1] for w in line_words)
            row_y0s.append(y0)
            
    # Also append terminator y
    row_y0s.append(terminator_y - 1)

    return sorted(row_y0s)

def find_text_y(page, text):
    """Return the y-coordinate of the first occurrence of text within clip."""
    words = page.get_text("words")

    from collections import defaultdict
    lines = defaultdict(list)

    # Group words into lines
    for word in words:
        x0, y0, x1, y1, word_text, block, line, word_no = word
        lines[(block, line)].append(word)

    for line_words in lines.values():
        line_words.sort(key=lambda w: w[0])

        line_text = " ".join(w[4] for w in line_words)

        if text in line_text:
            if text == "SUB TOTAL CARRIED FORWARD TO NEXT PAGE":
                return min(w[1] for w in line_words)
            elif text == "CLOSING BALANCE": # We want to include this line for final check
                return min(w[3] for w in line_words)

    return None

"""
Get the Transactions
"""
    
def get_transactions(pdf_path: str):
    doc = check_page_rotation(pdf_path)
    yr_rollover_flag = False
    period_years = statement_years(doc)
    print(f"Number of year in the statement period: {len(period_years)}")
    if len(period_years) == 1:
        year = period_years[0]
    else:
        year = period_years[0]
        yr_rollover_flag = True
        
    # Date format of pdf, and what is needed for QIF format
    date_format = "%d %b %Y"
    
    amnt_checks = get_balances(doc[0])
    if amnt_checks is not None:
        init_credits, init_debits, diff_amount = amnt_checks[0], amnt_checks[1], amnt_checks[2]
        
    running_balance, init_closing_balance = amnt_checks[3], amnt_checks[4]
    
    init_opening_balance = amnt_checks[3]
    
    comb_data = [['Date', 'Transaction Details', 'Amount']]
    t_line = 0     
    tot_running = 0
    tot_debit = 0
    tot_credit = 0
    
    closing_flag = False 
    opening_flag = False

    #x_values = get_x_coords(doc[0])
    
    for page in doc:
        remove_annots(page)
        # To skip empty pages
        if not page.get_text():
            continue
        
        x_values = get_x_coords(page)
        y_values = get_table_row_ys(page)
        
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
                    if not text:
                        break
                    # Checks the first instance of ' JAN ' and if year rollover flag is raised; if so then update year
                    if is_datetime(str(text[:6] + " " + year), date_format) and (text[2:6] == ' JAN') and yr_rollover_flag:
                        year = period_years[1]
                        yr_rollover_flag = False    
                    # Checks whether line is a date using datetime function; also adds start of transaction name
                    if is_datetime(str(text[:6] + " " + year), date_format):
                        comb_data[t_line+1].append(reformat_date(str(text[:6] + " " + year)))
                    else:
                        break
                elif j == 1:
                    if text[-15:] == 'CLOSING BALANCE':
                        closing_flag = True
                        comb_data[t_line+1].pop()
                    elif text[:15] == 'OPENING BALANCE':
                        opening_flag = True
                        comb_data[t_line+1].pop()
                    else:
                        comb_data[t_line+1].append(text)
                elif j == 2:
                    if text:
                        amount_str = str(text.split()[0].replace(',', '').strip())
                        comb_data[t_line+1].append('-' + amount_str)
                        running_balance -= float(amount_str)
                        tot_running -= float(amount_str)
                        tot_debit -= float(amount_str)
                elif j == 3:
                    if text:
                        amount_str = str(text.split()[0].replace(',', '').strip())
                        comb_data[t_line+1].append(amount_str)
                        running_balance += float(amount_str)
                        tot_running += float(amount_str)
                        tot_credit += float(amount_str)
                elif j == 4:
                    if opening_flag == True:
                        opening_balance = round(float(text.split()[0].replace(',', '').strip()), 2)
                        print(f"Obtained opening balance: ${round(opening_balance, 2)}")
                        if round(opening_balance, 2) == init_opening_balance:
                            print("Opening balance at start of statement and initial opening balance match")
                            opening_flag = False
                            break
                        else:
                            raise (ValueError(f"Opening balance and initial opening balance do not match: {round(opening_balance, 2)}, {init_opening_balance} \n \
                                        Find at row: {i}"))                   
                    elif closing_flag == True:
                        closing_balance = round(float(text.split()[0].replace(',', '').strip()), 2)
                        print(f"Obtained closing balance: ${round(closing_balance, 2)}")
                        if round(closing_balance, 2) == init_closing_balance:
                            print("Closing balance at end of statement and initial closing balance match")
                        else:
                            raise (ValueError(f"Closing balance and initial closing balance do not match: {round(closing_balance, 2)}, {init_closing_balance} \n \
                                        Find at row: {i}"))
                        diff_amount = round(closing_balance - opening_balance, 2)
                        print(f"Obtained difference between opening and closing balance: ${diff_amount}")
                        print(f"-------------------------------------------------")
                        break
                    
                    if text[-1] == '-':
                        given_balance = -round(float(text.split()[0].replace(',', '').strip()), 2)
                    else:
                        given_balance = round(float(text.split()[0].replace(',', '').strip()), 2)

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
Convert BOM pdf depending on statement type
"""
def convert_bom(pdf_path: str):
    data = get_transactions(pdf_path)
    csv_name = (os.path.splitext(os.path.basename(pdf_path))[0] + '.csv')
    export_to_csv(data, (os.path.dirname(pdf_path) + '/' + csv_name))
    return csv_rename(pdf_path)