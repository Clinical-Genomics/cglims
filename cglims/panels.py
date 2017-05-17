# -*- coding: utf-8 -*-
"""Handle gene panels."""

COLLABORATORS = ('cust000', 'cust002', 'cust003', 'cust004', 'cust042')
MASTER_LIST = ('ENDO', 'EP', 'IEM', 'IBMFS', 'mtDNA', 'MIT', 'PEDHEP', 'OMIM-AUTO',
               'PIDCAD', 'PID', 'SKD', 'NMD', 'ATX', 'CTD', 'ID', 'SPG', 'Ataxi', 'AD-HSP')
COMBOS = {
    'DSD': ('DSD', 'HYP', 'SEXDIF', 'SEXDET'),
    'CM': ('CNM', 'CM'),
    'Horsel': ('Horsel', '141217', '141201'),
}


def convert_panels(customer, default_panels):
    """Convert between default panels and all panels included in gene list."""
    if customer in COLLABORATORS:
        # check if all default panels are part of master list
        if all(panel in MASTER_LIST for panel in default_panels):
            return MASTER_LIST

    # the rest are handled the same way
    all_panels = set(default_panels)

    # fill in extra panels if selection is part of a combo
    for panel in default_panels:
        if panel in COMBOS:
            for extra_panel in COMBOS[panel]:
                all_panels.add(extra_panel)

    # add OMIM to every panel choice
    all_panels.add('OMIM-AUTO')

    return list(all_panels)
