import csv
from datetime import datetime
import os
import pymupdf
import fitz
from dateutil import parser
from pathlib import Path

# From https://stackoverflow.com/questions/72916381/read-specific-region-from-pdf
# For visualizing the rects that PyMuPDF uses compared to what you see in the PDF
def vis_pdf(input_path):
    doc = pymupdf.open(input_path)
    rect = fitz.Rect(0,10,600,740)
    page = doc[0]
    # Draw a red box to visualize the rect's area (text)
    page.draw_rect(rect, width=1.5, color=(1, 0, 0))
    head, tail = os.path.split(input_path)
    viz_name = os.path.join(head, "viz_" + tail)
    doc.save(viz_name)
    
# Function to check whether line is a date using datetime
def is_datetime(line, date_format):
    try:
        datetime.strptime(line, date_format)
        return True
    except ValueError:
        return False

# Export data array from pdf to csv
def export_to_csv(data, output_file):
    with open(output_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(data)

# To parse datetime
def reformat_date(date: str, output_format: str = "%d/%m/%y") -> str | None:
    try:
        dt = parser.parse(date, dayfirst=True) # AUS day is first in statements
    except (ValueError, OverflowError):
        return None
    return dt.strftime(output_format)

def csv_rename(pdf_path: str):
    return str(Path(pdf_path).with_suffix(".csv")).replace(' ', '_')