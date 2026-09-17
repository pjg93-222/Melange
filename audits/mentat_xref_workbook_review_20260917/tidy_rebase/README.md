# Tidy patches rebased onto HEAD 3fdfeae8f (2026-09-17)

P5-rebased.patch: build_industry_report.ps1 tidy step, HEAD-anchored; git apply --check --cached passes; PowerShell parse 0 errors.
P6c and P7b: NOT rebaseable. P6c edits inside def worksheet_accounting(), which exists only in the other lane's UNCOMMITTED report_insights.py (absent from HEAD); P7b's test uses the self.book() helper that likewise exists only in that lane's uncommitted test file. Both must follow that lane's commit, then apply from the tidy packet (they are already applied in the working tree).
