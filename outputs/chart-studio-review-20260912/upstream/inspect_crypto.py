from pathlib import Path
import json, sys
import openpyxl
sys.path.insert(0, r'C:\Users\pgoff\Mentat\mentat\tools')
from report_directory import report_directory
path=report_directory()/'Crypto Industry Spending Overview.xlsx'
book=openpyxl.load_workbook(path, read_only=True, data_only=True)
names=['2023-2024','2025-2026','2023-2024 Summary','Crypto Spending Overview','Recipient List','Beneficiary Bridge','Downstream Activity']
out={}
for name in names:
    sheet=book[name]
    rows=[]
    for row in sheet.iter_rows(max_row=9):
        rows.append({c.coordinate:c.value for c in row if c.value is not None})
    out[name]=rows
print(json.dumps(out,indent=2,default=str))
book.close()
