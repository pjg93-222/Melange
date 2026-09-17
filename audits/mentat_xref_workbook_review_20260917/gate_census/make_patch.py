"""Build the D2 patch in the scratchpad. Reads report.R from git HEAD via a
dump the caller provides; writes only into this directory."""
import os, sys

OUT = os.path.dirname(os.path.abspath(__file__))
orig_path = os.path.join(OUT, 'report_orig.R')
patched_path = os.path.join(OUT, 'report_patched.R')

with open(orig_path, 'rb') as f:
    raw = f.read()
crlf = raw.count(b'\r\n')
print('CRLF line endings:', crlf, ' LF-only:', raw.count(b'\n') - crlf)
text = raw.decode('utf-8')
nl = '\r\n' if crlf else '\n'

OLD_PROJ = (
    '  receipt_projection <- function(table) {\n'
    '    fields <- c("receipt_type_full", "filing_form", "receipt_type", "line_number", "line_number_label",\n'
    '                "file_num", "report_year", "report_type",\n'
    '                "memo_code", "memoed_subtotal", "memo_text", "back_reference_transaction_id", "back_reference_schedule_name")\n'
    '    present <- DBI::dbListFields(connection, table)\n'
    '    paste0(paste(vapply(fields, function(field) {\n'
    '      if (field %in% present) field else paste0("NULL AS ", field)\n'
    '    }, character(1L)), collapse = ", "), ",")\n'
    '  }\n'
)

NEW_PROJ = (
    '  optional_projection <- function(table, fields) {\n'
    '    present <- DBI::dbListFields(connection, table)\n'
    '    paste0(paste(vapply(fields, function(field) {\n'
    '      if (field %in% present) field else paste0("NULL AS ", field)\n'
    '    }, character(1L)), collapse = ", "), ",")\n'
    '  }\n'
    '  receipt_projection <- function(table) {\n'
    '    optional_projection(table, c(\n'
    '      "receipt_type_full", "filing_form", "receipt_type", "line_number", "line_number_label",\n'
    '      "file_num", "report_year", "report_type",\n'
    '      "memo_code", "memoed_subtotal", "memo_text", "back_reference_transaction_id", "back_reference_schedule_name"))\n'
    '  }\n'
    '  # contributor_street_1/2 arrived with the street-column migration. Snapshots\n'
    '  # taken before it do not carry the columns, and SELECTing them\n'
    '  # unconditionally aborts the whole export with "no such column" before any\n'
    '  # guard downstream can run. Give them the same tolerance the receipt\n'
    '  # metadata above already has: absent means blank, never a failed export.\n'
    '  street_projection <- function(table) {\n'
    '    optional_projection(table, c("contributor_street_1", "contributor_street_2"))\n'
    '  }\n'
)

OLD_SEL = ('      "contributor_zip, contributor_employer, contributor_occupation,'
           ' contributor_street_1, contributor_street_2, company, sub_id,'
           ' matched_variant,",\n')


def new_sel(table):
    return ('      "contributor_zip, contributor_employer, contributor_occupation,",\n'
            '      %s("%s"), "company, sub_id, matched_variant,",\n'
            % ('street_projection', table))


work = text.replace('\r\n', '\n')

assert work.count(OLD_PROJ) == 1, 'receipt_projection block not found exactly once'
work = work.replace(OLD_PROJ, NEW_PROJ)

assert work.count(OLD_SEL) == 2, 'expected exactly 2 street SELECT lines, got %d' % work.count(OLD_SEL)
# First occurrence is the contributions SELECT, second is corporate_giving.
head, rest = work.split(OLD_SEL, 1)
work = head + new_sel('contributions') + rest
head, rest = work.split(OLD_SEL, 1)
work = head + new_sel('corporate_giving') + rest

assert 'contributor_street_1, contributor_street_2, company' not in work
assert work.count('street_projection(') == 2   # two call sites
assert work.count('street_projection <- function') == 1
assert work.count('optional_projection(table, ') == 2  # receipt + street

if nl == '\r\n':
    work = work.replace('\n', '\r\n')
with open(patched_path, 'w', newline='', encoding='utf-8') as f:
    f.write(work)
print('wrote report_patched.R')
