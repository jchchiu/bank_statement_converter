import subprocess
import shutil
from pathlib import Path

import pytest

# Adjust these to wherever your gold data lives:
BASE = Path(__file__).parent
PDF_DIR      = BASE / "data" / "test_folder"
GOLD_CSV_DIR = BASE / "data" / "gold" / "csv"
GOLD_QIF_DIR = BASE / "data" / "gold" / "qif"

CLI_CMD = "bstc"

PDFS = sorted(PDF_DIR.glob("*.pdf"))

# Using a custom id function to show the file name
@pytest.mark.parametrize("pdf_path", PDFS, ids=[pdf.name for pdf in PDFS])
def test_pdf_to_csv_and_qif(tmp_path, file_regression, pdf_path):
    """
    For each PDF in tests/data/pdfs/:
      - copy into tmp_path
      - run `bstc file <pdf> -q`
      - feed both outputs to file_regression.check()
    """
    # 1) copy the test PDF into our scratch dir
    work_pdf = tmp_path / pdf_path.name
    shutil.copy(pdf_path, work_pdf)

    # 2) invoke your CLI, in that scratch dir
    cmd = [CLI_CMD, "file", str(work_pdf), "-q"]
    res = subprocess.run(cmd,
                         cwd=tmp_path,
                         capture_output=True,
                         text=True)
    assert res.returncode == 0, (
        f"CLI failed on {pdf_path.name}\n"
        f"stdout:\n{res.stdout}\n"
        f"stderr:\n{res.stderr}"
    )

    stem = pdf_path.stem
    out_csv = tmp_path / f"{stem}.csv"
    out_qif = tmp_path / f"{stem}.qif"

    assert out_csv.exists(), f"{out_csv} was not created"
    assert out_qif.exists(), f"{out_qif} was not created"

    # 3) compare the bytes of each file against your gold dirs
    csv_bytes = out_csv.read_bytes()
    qif_bytes = out_qif.read_bytes()

    # file_regression will look for:
    #    GOLD_CSV_DIR / "<basename>.csv"
    #    GOLD_QIF_DIR / "<basename>.qif"
    #
    # and will error if they differ.
    file_regression.check(
        csv_bytes,
        binary=True,
        fullpath=str(GOLD_CSV_DIR / f"{stem}.csv")
    )
    file_regression.check(
        qif_bytes,
        binary=True,
        fullpath=str(GOLD_QIF_DIR / f"{stem}.qif")
    )
