import argparse
from pathlib import Path
from .cba_converter import convert_cba
from .anz_converter import convert_anz
from .nab_converter import convert_nab
from .wbc_converter import convert_wbc
from .bank_detector import detect_bank
from .csv2qif import csv_to_qif

def main():
    p = argparse.ArgumentParser(prog = 'bstc',
                                description = 'Convert bank PDF -> CSV or CSV -> QIF')
    subs = p.add_subparsers(dest='cmd')
    
    # Command for auto-detect bank
    auto = subs.add_parser('auto', help = 'Automatically detect the bank statement and convert pdf to CSV or QIF')
    auto.add_argument('pdf_path')
    auto.add_argument('--qif', nargs = '?', const = '', metavar = 'QIF',
                      help='Further convert csv to qif')
    
    # Commands for the different banks
    cba = subs.add_parser('cba', help = 'cba PDF -> CSV')
    cba.add_argument('pdf_path')
    
    anz = subs.add_parser('anz', help = 'anz PDF -> CSV')
    anz.add_argument('pdf_path')
    
    nab = subs.add_parser('nab', help = 'nab PDF -> CSV')
    nab.add_argument('pdf_path')
    
    wbc = subs.add_parser('wbc', help = 'wbc PDF -> CSV')
    wbc.add_argument('pdf_path')        
    
    # Command for csv2qif
    q = subs.add_parser('csv2qif', help = 'CSV -> QIF only')
    q.add_argument('csv_path')
    

    args = p.parse_args()
    
    def pdf2csv_qif(pdf_path: str, qif_flag):
        bank = detect_bank(pdf_path)
        if not bank:
            raise ValueError("Could not detect bank from PDF.")
        print(f"Detected bank: {bank}")
        print(f"-------------------------------------------------")
        
        if bank == 'cba':
            convert_cba(pdf_path)
            print("Success! Your CBA statement has been converted from pdf to csv.")
            
        if bank == 'nab':
            convert_nab(pdf_path)
            print("Success! Your NAB statement has been converted from pdf to csv.")
            
        if bank == 'anz':
            convert_anz(pdf_path)
            print("Success! Your ANZ statement has been converted from pdf to csv.")
            
        if bank == 'wbc':
            convert_wbc(pdf_path)
            print("Success! Your Westpac statement has been converted from pdf to csv.")
            
        if qif_flag is not None:
            print("--------Flag for converting to qif raised--------")
            csv_to_qif(str(Path(pdf_path).with_suffix(".csv")).replace(' ', '_'))
            print(f"Success! Your {bank} statement has been converted from csv to qif.")
    
    # Dispatch
    if args.cmd == 'auto':
        pdf2csv_qif(args.pdf_path, args.qif)
    elif args.cmd == 'cba':
        convert_cba(args.pdf_path)
    elif args.cmd == 'anz':
        convert_anz(args.pdf_path)
    elif args.cmd == 'nab':
        convert_nab(args.pdf_path)
    elif args.cmd == 'wbc':
        convert_wbc(args.pdf_path)
    elif args.cmd == 'csv2qif':
        csv_to_qif(args.csv_path)
        return ('Success! Your csv has been converted to qif.')
    
    else:
        p.print_help()
        
if __name__ == '__main__':
    main()