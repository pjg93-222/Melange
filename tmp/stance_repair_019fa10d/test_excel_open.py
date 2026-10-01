import sys
import win32com.client as win32

excel = win32.DispatchEx("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False
try:
    for path in sys.argv[1:]:
        book = None
        try:
            book = excel.Workbooks.Open(path, UpdateLinks=0, ReadOnly=True)
            print("OPEN_OK", path, len(book.Worksheets))
        except Exception as exc:
            print("OPEN_FAIL", path, repr(exc))
        finally:
            if book is not None:
                book.Close(SaveChanges=False)
finally:
    excel.Quit()
