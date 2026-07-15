# -*- coding: utf-8 -*-
"""Single source of the project root (architecture review 2026-07-02).
Override with the MONEYBALL_ROOT environment variable — every script resolves
its paths from here, so relocating the project (or escaping OneDrive) is a
one-variable change instead of a 95-file edit."""
import os
_HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.abspath(os.environ.get('MONEYBALL_ROOT',os.path.join(_HERE,os.pardir)))
DRAFT=os.path.abspath(os.environ.get('MONEYBALL_DRAFT',os.path.join(ROOT,os.pardir,'Draft Systems')))   # R press-pipeline root
FEC=os.path.join(ROOT,'fec')
WORKBOOK=os.path.join(ROOT,'Moneyball Main Version - Blended.xlsx')
BACKUPS=os.path.join(ROOT,'backups')
def p(*parts): return os.path.join(ROOT,*parts)
