import csv
import os.path
from datetime import datetime
import fitz
import re

# SPACE SO SOMETHING LIKE "TO MARINE" DOESN'T FLAG; NOTE MAY NOT WORK IF "....MAR "
months = ['JAN ', 'FEB ', 'MAR ', 'APR ', 'MAY ', 'JUN ', 
          'JUL ', 'AUG ', 'SEP ', 'OCT ', 'NOV ', 'DEC ']

def lowercase_month(month):
    return month[:-2] + month[-2:].lower()

def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False

# Function to extract text from a rectangular area on a PDF page
def text_from_area(file, page_number=None):
    doc = fitz.open(file)
    
    # For page 0 we get the opening and closing balance; can compare the difference at end to confirm matching
    if page_number == 0:
        page = doc[page_number]
        rect = fitz.Rect(10,300,600,800)
        text = page.get_text(clip=rect)       
#        print(text)
        return text
    
    # For all other pages the rectangle is higher in height to get all transactions
    else:
        text = ''
        rect = fitz.Rect(10,140,500,1200)
        for page_number in range(1,doc.page_count):
            page = doc[page_number]
            text += page.get_text(clip=rect) + "\n"
        
    return text

# Function to get the difference in the opening and closing balance on page 0; ALSO THE COMPANY NAME
# Input: text from pdf of first page (page 0)
# Output: [0] is the difference in the opening and closing balance; [1] is the company name
def difference_sum(text):
    #INCLUDE FLAG TO GET OWNERS NAME?
    client_name = ''
    client_flag = False
    
    page0_flag = False
    diff_sum = 0  
    # closing is needed to get diff in one variable
    closing = False
    # skip is needed as after the 'Closing Balance:' the amount is not on the next line but the one after
    skip = False
    
    for line in text:
        if page0_flag == True:
            if skip == True:
                skip = False
                continue
            if closing == True:
                diff_sum += float(line.replace('$', '').replace(',', '').strip())
                break
            diff_sum -= float(line.replace('$', '').replace(',', '').strip())
            page0_flag = False
        if re.search(r'\bOpening Balance:', line):
            page0_flag = True
            continue
        if re.search(r'\bClosing Balance:', line):
            page0_flag = True
            skip = True
            closing = True
            continue
        if client_flag == True:
            client_name = line
            client_flag = False
            continue
        if re.search(r'\bAccount Details', line):
            client_flag = True
            
    return round(diff_sum, 2), client_name

# Get data for the withdraw account; may need to add more re.search parameters
# Input: text from pdf
# Output: [0] is the combined data of date, transactions, amounts; [1] is the sum of the amounts
def get_data_withdraw(text):
    lines = text.split('\n')
    dates = []
    amounts = []
    transactions = []
    
    skip = 0
    year = lines[4].strip()
    years = ['2024', '2025']
    
    # To get to extra information on next line, when current line does not have any info
    prev_line = ''
    prev_flag = False
    date_flag = False
    
    # For checking whether it is a withdrawal or deposit
    blank_flag = False
    data_sum = 0
    
    new_datef = "%d-%b-%y"
    date_format = "%d %b %Y"
    
    for line in lines:
#        print(line)
        if skip > 0:
#           print('skipped')
            skip -= 1
            continue
        
        if line.strip() in years:
            year = line.strip()
            continue
        
        # Checks whether the line is a date line
        if line[3:7] in months:
#            print(len(line))
            if len(line) == 7: # If date is not combined with transaction
                dates.append(datetime.strptime(lowercase_month(line) + year, date_format).
                             strftime(new_datef))
            else: # If the date is combined with the transaction
                dates.append(datetime.strptime(lowercase_month(line[:7]) + year, date_format).
                             strftime(new_datef))
                split_transaction = line[7:]
                date_flag = True
                blank_flag = False # Reset blank flag at every transaction
                if (re.search(r'\bPAYMENT', split_transaction) or re.search(r'\bATM', line) or \
                    re.search(r'\bBANKING', split_transaction)) and (date_flag == True):
                    prev_line = split_transaction
                    prev_flag = True
                    date_flag = False
                    continue
                else:
                    transactions.append(split_transaction.strip())
                    continue
            date_flag = True
            blank_flag = False # Reset blank_line flag at every transaction
            continue 
        
        # Combine current line with previous line for more info; then reset previous line flag
        if prev_flag == True:
            transactions.append((prev_line + line).strip())
            prev_flag = False
            continue
        
        # To get to extra information on next line, when current line does not have any info
        if (re.search(r'\bPAYMENT', line) or re.search(r'\bATM', line) or \
            re.search(r'\bBANKING', line)) and (date_flag == True):
            prev_line = line
            prev_flag = True
            date_flag = False
            continue
        
        # Phrases which are only one line so don't need next line for more info
        if re.search(r'\bDEBIT INTEREST CHARGED', line) or \
           re.search(r'\bCREDIT INTEREST PAID', line) or \
           re.search(r'\bHONOUR/OVERDRAWN FEE', line) or \
           re.search(r'\bDEPOSIT', line):
            transactions.append(line.strip())
            continue     
        
        # Float check to see whether the line is a transaction
        if is_float(line.replace(',', '').strip()):
            float_str = line.replace(',', '').strip()
            if float(float_str) == float(year):
                continue
            if blank_flag == True:
                amounts.append(float_str)
                data_sum += float(float_str)
            else:
                amounts.append('-' + float_str)
                data_sum -= float(float_str)    
            continue
        
        # If the line is a blank, throw a flag; if the flag is True then it is a deposit; if False then it is a withdrawal
        # If a blank flag is True before a float is found, that means that the amount is in the deposit column
        if re.search(r'\bblank', line):
            blank_flag = True
            continue
        
        # Skips the "Totals at end of page" line and next two blank spaces
        if re.search(r'\bTOTALS AT END OF PAGE', line):
            skip = 2
            continue
        # Ends loop when it reaches end of statement
        if re.search(r'\bTOTALS AT END OF PERIOD', line):
            break
    
    dates.pop(0)
    
    # If the Opening Statement is on the same line as the first date
    if transactions[0] == 'OPENING BALANCE':
        transactions.pop(0)
 #   print(dates)
 #   print(transactions)
 #   print(amounts)
 #   print(data_sum)
 # WRITE A TEST TO VERIFY ALL DATA ARRAYS ARE THE SAME LENGTH
    print(len(dates), len(transactions), len(amounts))
    
    # Combine the data into a single array so it is easier to convert to csv
    comb_data = [['Date', 'Amount', 'Transaction Details']]
    for i in range(len(dates)):
        comb_data.append([dates[i], amounts[i], transactions[i]])

    return comb_data, round(data_sum, 2)
        
# Get data for the deposit account; may need to add more re.search parameters
# Input: text from pdf
# Output: [0] is the combined data of date, transactions, amounts; [1] is the sum of the amounts        
def get_data_deposit(text):
    lines = text.split('\n')
    dates = []
    amounts = []
    transactions = []
    
    skip = 0
    year = lines[4].strip()
    years = ['2024', '2025']
    
    # To get to extra information on next line, when current line does not have any info
    prev_line = ''
    prev_flag = False
    date_flag = False
    
    new_datef = "%d-%b-%y"
    date_format = "%d %b %Y"
    
    # For checking whether it is a withdrawal or deposit
    blank_flag = False
    data_sum = 0
    
    for line in lines:
        print(line)
        if skip > 0:
#           print('skipped')
            skip -= 1
            continue
        
        if line.strip() in years:
            year = line.strip()
            continue
        
        # Checks whether the line is a date line
        if line[3:7] in months:
#            print(len(line))
            if len(line) == 7: # If date is not combined with transaction
                dates.append(datetime.strptime(lowercase_month(line) + year, date_format).
                             strftime(new_datef))
            else: # If the date is combined with the transaction
                dates.append(datetime.strptime(lowercase_month(line[:7]) + year, date_format).
                             strftime(new_datef))
                split_transaction = line[7:]
                date_flag = True
                blank_flag = False # Reset blank flag at every transaction
                if (re.search(r'\bPURCHASE', split_transaction) or re.search(r'\bATM', split_transaction) or \
                    re.search(r'\bTRANSFER', split_transaction) or re.search(r'\bPAYMENT', split_transaction) or \
                    re.search(r'\bTFER', split_transaction) or re.search(r'\bBPAY', split_transaction)) and (date_flag == True):
                    prev_line = split_transaction
                    prev_flag = True
                    date_flag = False
                    continue
                else:
                    transactions.append(split_transaction.strip())
                    continue
            date_flag = True
            blank_flag = False # Reset blank_line flag at every transaction
            continue 
        
        # Combine current line with previous line for more info; then reset previous line flag
        if prev_flag == True:
            if re.search(r'\bblank', line):
                blank_flag = True
                transactions.append((prev_line).strip())
                prev_flag = False
                continue
            transactions.append((prev_line + line).strip())
            prev_flag = False
            continue
        
        # To get to extra information on next line, when current line does not have any info
        if (re.search(r'\bPURCHASE', line) or re.search(r'\bATM', line) or \
            re.search(r'\bTRANSFER', line) or re.search(r'\bPAYMENT', line)  or \
            re.search(r'\bTFER', line) or re.search(r'\bBPAY', line)) and (date_flag == True):
            prev_line = line
            prev_flag = True
            date_flag = False
            continue
        
        # Phrases which are only one line so don't need next line for more info
        if re.search(r'\bACCOUNT SERVICING FEE', line) or \
           re.search(r'\bCREDIT INTEREST PAID', line) or \
           re.search(r'\bHONOUR/OVERDRAWN FEE', line) or \
           re.search(r'\bDEPOSIT', line) or \
           re.search(r'\bWITHDRAWAL', line) or \
           line[:2] == '00': # For transfers starting with '00'
            transactions.append(line.strip())
            continue     
        
        # Float check to see whether the line is a transaction
        if is_float(line.replace(',', '').strip()):
            float_str = line.replace(',', '').strip()
            if float_str == year:
                continue
            if blank_flag == True:
                amounts.append(float_str)
                data_sum += float(float_str)
            else:
                amounts.append('-' + float_str)
                data_sum -= float(float_str)    
            continue
        
        # If the line is a blank, throw a flag; if the flag is True then it is a deposit; if False then it is a withdrawal
        # If a blank flag is True before a float is found, that means that the amount is in the deposit column
        if re.search(r'\bblank', line):
            blank_flag = True
            continue
        
        # Skips the "Totals at end of page" line and next two blank spaces
        if re.search(r'\bTOTALS AT END OF PAGE', line):
            skip = 2
            continue
        # Ends loop when it reaches end of statement
        if re.search(r'\bTOTALS AT END OF PERIOD', line):
            break
    
    dates.pop(0)
    if transactions[0] == 'OPENING BALANCE':
        transactions.pop(0)
    print(dates)
    print(transactions)
    print(amounts)
    print(data_sum)
    print(len(dates), len(transactions), len(amounts))
    
    # Combine the data into a single array so it is easier to convert to csv
    comb_data = [['Date', 'Amount', 'Transaction Details']]
    for i in range(len(dates)):
        comb_data.append([dates[i], amounts[i], transactions[i]])

    return comb_data, round(data_sum, 2)


# Function to convert array to csv if data sums match
def export_to_csv(data, output_file):
    with open(output_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(data)
    
def convert_anz(file, keyword):
    diff_sum = difference_sum(text_from_area(file, page_number=0).split('\n'))
    # flag 
    if keyword == 'withdraw':
        data = get_data_withdraw(text_from_area(file))
        print(diff_sum[0], data[1])
        csv_name = (os.path.splitext(os.path.basename(file))[0] + '_' + diff_sum[1].strip() + '_BAS.csv').replace(' ', '_').replace('/','')
        if diff_sum[0] == data[1]:
            export_to_csv(data[0], csv_name)
    if keyword == 'deposit':
        data = get_data_deposit(text_from_area(file))
        print(diff_sum[0], data[1])
        csv_name = (os.path.splitext(os.path.basename(file))[0] + '_' + diff_sum[1].strip() + '_BAS.csv').replace(' ', '_').replace('/','')
        if diff_sum[0] == data[1]:
            export_to_csv(data[0], csv_name)
    

#print(text_from_area(file, 1))

#get_data_withdraw(text_from_area(file_withdraw, 5))
#get_data_deposit(text_from_area(file_deposit, 1))
