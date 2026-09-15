"""Controls for the F1b A/B.

control_http.py   - the CURRENT test file against the PRE-FIX server.py
                    (mentat/app/server.py.bak-20260914-F1b). Tests held constant,
                    only the server differs.
control_f1.py     - the pre-F1 test file against the pre-F1 server, kept from
                    the earlier flake investigation.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SLASH = chr(92)
APP = "C:" + SLASH + "Users" + SLASH + "pgoff" + SLASH + "Mentat" + SLASH + "mentat" + SLASH + "app"

OLD = ('APP = Path(__file__).resolve().parents[1] / "app"\n'
       'spec = importlib.util.spec_from_file_location("contribution_http_server", APP / "server.py")')


def build(source, server_name, out_name, module_name):
    text = Path(source).read_text(encoding="utf-8")
    new = ('import importlib.machinery\n'
           'APP = Path(r"' + APP + '")\n'
           'spec = importlib.util.spec_from_loader("' + module_name + '",\n'
           '    importlib.machinery.SourceFileLoader("' + module_name + '", str(APP / "' + server_name + '")))')
    assert OLD in text, "anchor missing in " + str(source)
    (HERE / out_name).write_text(text.replace(OLD, new), encoding="utf-8")
    print("wrote", out_name, "->", server_name)


build(r"C:\Users\pgoff\Mentat\mentat\tests\test_contribution_http.py",
      "server.py.bak-20260914-F1b", "control_http.py", "control_http_server")
build(r"C:\Users\pgoff\Mentat\mentat\tests\test_contribution_http.py.bak-20260914-F1",
      "server.py.bak-20260914-F1", "control_f1.py", "control_f1_server")
