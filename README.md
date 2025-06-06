# Package for converting Australian pdf bank statements to csv or qif
Can be run as a CLI or with a GUI
While .qif and .csv can be downloaded directly from banks this program can be used if you only have pdf available
Files will be saved in the same folder as the pdf

Currently supports the following statements:
CBA: 
- Business Transaction Account 
- Has a running balance check for each transaction and a final closing balance check
ANZ: 
- BUSINESS ADVANTAGE STATEMENT/ BUSINESS ONLINE SAVER/ BUSINESS EXTRA
- Has a running balance check for each transaction and a final closing balance check   
NAB: 
- Transaction Account
- Has a final check between summed up transaction amounts and difference between opening and closing balance
Westpac (WBC): 
- Westpac Business One Plus
- MAY NOT WORK AS WELL -> Need to refine get_transactions function
- Has no check as there are no opening or closing balances for reference 

Currently only returns the following for the csv:
- Date of the transaction
- Transaction details
- Amount (credit or debit)

Also has a csv to qif converter that can be run independently or with the pdf -> csv conversion

Rough steps:
1. clone repo
2. create venv
 - go to root of package and run in cmd(python -m venv .venv)
3. go into .venv (.venv\Scripts\activate)
4. install packages
 - (pip install -r requirements.txt) or requirements-build.txt for pyinstaller launcher | then (pip install -e .)
 - or go to root of package and (pip install -e .) or (pip install -e .[build]) (if want pyinstaller launcher) to install packages required
5. run the package 
 - use 'bstc' and arguments or 'btsc-gui' only to open the GUI
6. create .exe if needed
 - (pyinstaller [--onefile] --windowed --name bstc-gui --paths src src/launcher_gui.py)