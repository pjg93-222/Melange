# -*- coding: utf-8 -*-
"""Lane F1 / self-check: prove f1_lib's transcribed rules are token-identical to the LIVE
producer source.  The LIVE files are read as TEXT and parsed with ast; nothing under fec/
is imported or executed.
"""
import ast, io, os, sys, tokenize
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LIVE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
MINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'f1_lib.py')


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def toplevel(src):
    """{name: source-segment} for every top-level def/class/assign in a module."""
    tree = ast.parse(src)
    out = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            out[node.name] = ast.get_source_segment(src, node)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out[target.id] = ast.get_source_segment(src, node)
    return out


def tokens(segment):
    """Comment/whitespace/docstring-insensitive token stream."""
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(segment).readline):
        if tok.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                        tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING,
                        tokenize.ENDMARKER):
            continue
        out.append((tok.type, tok.string))
    # drop a leading docstring expression statement
    while len(out) > 1 and out[0][0] == tokenize.STRING:
        out = out[1:]
    return out


def strip_docstrings(segment):
    """Remove every string-only statement so wording differences don't matter."""
    tree = ast.parse(segment)

    class Killer(ast.NodeTransformer):
        def visit_Expr(self, node):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return None
            return node
    return ast.dump(Killer().visit(tree))


mine = toplevel(read(MINE))
checks = [
    ('bill_rules.py', os.path.join(LIVE, 'fec', 'bill_rules.py'),
     ['canonical_category', 'bill_key', 'bill_type_key', 'role_weight',
      'canonical_role', 'preferred_role', 'CATEGORIES', 'LABEL_TO_CANONICAL',
      'SECTION_KEYWORDS']),
    ('members/member_identity.py', os.path.join(LIVE, 'fec', 'members', 'member_identity.py'),
     ['normalize_name', 'first_names_agree', 'Resolver', '_SUFFIXES',
      '_FIRST_EQUIV', '_MEMBER_ALIASES']),
]
rename = {'congress_of': '_congress'}
fails = 0
print('=' * 96)
print('F1 SELF-CHECK  transcribed rule parity vs the LIVE producer source (ast, docstring-insensitive)')
print('=' * 96)
for label, path, names in checks:
    live = toplevel(read(path))
    for name in names:
        a, b = live.get(name), mine.get(name)
        if a is None or b is None:
            print('  MISSING  %-22s live=%s mine=%s' % (name, a is not None, b is not None))
            fails += 1
            continue
        same = strip_docstrings(a) == strip_docstrings(b)
        print('  %-8s %-22s %s' % ('SAME' if same else 'DIFFERS', name, label))
        if not same:
            fails += 1
# _congress was transcribed under the name congress_of (leading underscore is private)
live_br = toplevel(read(os.path.join(LIVE, 'fec', 'bill_rules.py')))
a = live_br['_congress'].replace('_congress', 'congress_of', 1)
b = mine['congress_of']
same = strip_docstrings(a) == strip_docstrings(b)
print('  %-8s %-22s bill_rules.py  (renamed _congress -> congress_of)'
      % ('SAME' if same else 'DIFFERS', 'congress_of'))
fails += 0 if same else 1

# the sentinel admission mask and the contribution formula, quoted not transcribed
prod = read(os.path.join(LIVE, 'fec', 'legislation', 'build_archive_legislative.py')).splitlines()
print('\nLIVE producer lines this lane depends on '
      '(fec\\legislation\\build_archive_legislative.py):')
for n in (46, 47, 48, 49, 182, 248, 251, 259, 269, 270):
    print('  %4d | %s' % (n, prod[n - 1]))
live_bill = read(os.path.join(LIVE, 'fec', 'bill_rules.py')).splitlines()
print('\nLIVE fec\\bill_rules.py sponsor weight:')
for n in range(211, 220):
    print('  %4d | %s' % (n, live_bill[n - 1]))
print('\nSELF-CHECK %s (%d mismatches)' % ('PASS' if fails == 0 else 'FAIL', fails))
