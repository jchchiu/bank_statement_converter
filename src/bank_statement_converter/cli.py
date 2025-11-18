import argparse
import os
from pathlib import Path

from .bank_detector import detect_bank
from .csv2qif       import csv_to_qif
from .anz_converter import convert_anz
from .ben_converter import convert_ben
from .cba_converter import convert_cba
from .mqg_converter import convert_mqg
from .nab_converter import convert_nab
from .wbc_converter import convert_wbc
from .zel_converter import convert_zel

def pdf2csv_qif(pdf_path: str, do_qif: bool, rm_csv: bool):
    bank_info = detect_bank(pdf_path)
    bank = bank_info[0]
    account_type = bank_info[1]
    
    if not bank:
        raise ValueError(f"Could not detect bank from PDF: {pdf_path!r}")
    print(f"Detected bank: {bank.upper()}")
    print(f"Detected account type: {account_type.upper()}")
    print("-------------------------------------------------")

    # dispatch to the correct converter
    if bank == 'cba':
        csv_path = convert_cba(pdf_path)
    elif bank == 'nab':
        csv_path = convert_nab(pdf_path, account_type)
    elif bank == 'anz':
        csv_path = convert_anz(pdf_path)
    elif bank == 'wbc':
        csv_path = convert_wbc(pdf_path, account_type)
    elif bank == 'ben':
        csv_path = convert_ben(pdf_path)
    elif bank == 'zel':
        csv_path = convert_zel(pdf_path)
    elif bank == 'mqg':
        csv_path = convert_mqg(pdf_path)
    else:
        raise ValueError(f"No converter implemented for bank {bank!r}")

    print(f"Created CSV: {csv_path}")

    if do_qif:
        print("-------- Converting CSV to QIF --------")
        qif_path = csv_to_qif(csv_path)
        print(f"Created QIF: {qif_path}")
        
        if rm_csv:
            print("---------- Removing CSV File ----------")
            os.remove(csv_path)
            print(f"Removed CSV: {csv_path}")
            return [qif_path]
        
        return [csv_path, qif_path]

    return [csv_path]


def main():
    p = argparse.ArgumentParser(
        prog='bstc',
        description='Convert bank PDF → CSV (and optional QIF), or CSV → QIF'
    )
    subs = p.add_subparsers(dest='cmd')

    # file: auto-detect PDF → CSV(/QIF)
    file_p = subs.add_parser(
        'file',
        help='Auto-detect bank, convert one PDF → CSV (optional QIF)'
    )
    file_p.add_argument('pdf_path', help="Path to the input PDF")
    file_p.add_argument(
        '-q', '--qif', action='store_true',
        help="Also convert the resulting CSV to QIF"
    )
    file_p.add_argument(
        '-r', '--rm_csv', action='store_true',
        help="Remove intermediary CSV after conversion to QIF (use in conjunction with -q)"
    )

    # folder: batch-convert all PDFs in a folder
    fld_p = subs.add_parser(
        'folder',
        help='Convert all PDFs in a folder → CSV (optional QIF)'
    )
    fld_p.add_argument('folder_path', help="Path to folder containing PDFs")
    fld_p.add_argument(
        '-q', '--qif', action='store_true',
        help="Also convert each CSV to QIF"
    )
    fld_p.add_argument(
        '-r', '--rm_csv', action='store_true',
        help="Remove intermediary CSV after conversion to QIF (use in conjunction with -q)"
    )

    # csv2qif: single CSV → QIF
    csv_p = subs.add_parser(
        'csv2qif',
        help='Convert one CSV → QIF'
    )
    csv_p.add_argument('csv_path', help="Path to the input CSV")

    args = p.parse_args()
    if args.cmd == 'file':
        outputs = pdf2csv_qif(args.pdf_path, args.qif, args.rm_csv)

    elif args.cmd == 'folder':
        folder = Path(args.folder_path)
        if not folder.is_dir():
            p.error(f"{folder!r} is not a directory")
        pdfs = sorted(folder.glob("*.pdf"))
        if not pdfs:
            print(f"No PDFs found in {folder}")
            return

        all_out = []
        for pdf in pdfs:
            print(f"\n=== Processing {pdf.name} ===")
            try:
                outs = pdf2csv_qif(str(pdf), args.qif, args.rm_csv)
                all_out.extend(outs)
            except Exception as e:
                print(f"ERROR on {pdf.name}: {e}")

        print("\nBatch complete. Files generated:")
        for f in all_out:
            print(" ", f)

    elif args.cmd == 'csv2qif':
        qif = csv_to_qif(args.csv_path)
        print(f"Created QIF: {qif}")

    else:
        p.print_help()


if __name__ == '__main__':
    main()
