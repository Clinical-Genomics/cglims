# -*- coding: utf-8 -*-
"""Handle gene panels."""

COLLABORATORS = ('cust000', 'cust002', 'cust003', 'cust004')
MASTER_LIST = ('ENDO', 'EP', 'IEM', 'IBMFS', 'mtDNA', 'MIT', 'OMIM', 'PIDCAD',
               'PID', 'SKD')
COMBOS = {
    'ATX': ('ATX', 'SPG', 'Ataxi', 'LARGE', 'AD-HSP'),
    'DSD': ('DSD', 'HYP', 'SEXDIF', 'SEXDET'),
    'CM': ('CNM', 'CM'),
    'Horsel': ('Horsel', '141217', '141201'),
    'NMD': ('HMSN', 'MM', 'OM', 'CMD', 'ACM', 'HP', 'OND', 'MS', 'HCM', 'NMD',
            'MD', 'CM', 'IC', 'MND', 'NM', 'CMS', 'DM', 'CRD', 'HA'),
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

    if customer == 'cust002':
        # add OMIM to every panel choice
        all_panels.add('OMIM')

    return list(all_panels)
