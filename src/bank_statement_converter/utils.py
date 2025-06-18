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
def reformat_date(date: str, output_format: str = "%d/%m/%Y") -> str | None:
    try:
        dt = parser.parse(date, dayfirst=True) # AUS day is first in statements
    except (ValueError, OverflowError):
        return None
    return dt.strftime(output_format)

def csv_rename(pdf_path: str):
    return str(Path(pdf_path).with_suffix(".csv"))

def remove_annots(page):
    if page.annots():
        for annot in page.annots():
            page.delete_annot(annot)
    return page

# ADAPTED FROM: https://github.com/pymupdf/PyMuPDF/discussions/1842
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