import csv
import itertools
from pathlib import Path
from .utils import reformat_date

def csv_to_qif(csv_filename: str):
    
    with open(csv_filename, 'r', newline='') as csv_file:
        csv_read = csv.DictReader(csv_file)
        
        # Make copy of csv to check first row as iteration will skip
        csv_read, read_copy = itertools.tee(csv_read)
        
        # Check whether the date
        date_flag = False
        try:
            first_row = next(read_copy)
            if 'Date' in first_row:  # May have issues here if csv doesn't have 'Date' header for date
                date_flag = True
        except StopIteration:
            pass 
        
        with open(Path(csv_filename).with_suffix(".qif"), 'w') as qif_file:
            qif_file.write(f"!Type:Bank \n")    
            
            if date_flag == False:
                csv_file.seek(0)
                csv_read_list = csv.reader(csv_file)
                for row in csv_read_list:
                    date = reformat_date(row[0])
                    if row[1][0] == '+':
                        amount = row[1][1:]
                    else:
                        amount = row[1]
                    details = row[2]
 
                    qif_file.write(f"D{date}\n")    
                    qif_file.write(f"T{amount}\n")
                    qif_file.write(f"P{details}\n")
                    qif_file.write(f"^\n")
                    
            else:
                for row in csv_read:
                    date = reformat_date(row['Date'])
                    amount = row['Amount']
                    if 'Transaction Details' in row:
                        details = row['Transaction Details']
                    if 'Description' in row:
                        details = row['Description']
                                        
                    qif_file.write(f"D{date}\n")    
                    qif_file.write(f"T{amount}\n")
                    qif_file.write(f"P{details}\n")
                    qif_file.write(f"^\n")
                    
    return str(Path(csv_filename).with_suffix(".qif"))