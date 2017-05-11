# -*- coding: utf-8 -*-
from cglims.constants import READS_PER_1X

PANELS = set(['EXO', 'EXT', 'MHP', 'EFT', 'CCP', 'EXX'])
WHOLEGENOME = set(['WGS', 'WGT', 'WGL', 'MWG', 'MWL', 'MWX', 'MET', 'MEL'])
ANALYSIS_ONLY = set(['EXX', 'WGX'])
MICROBIAL = set(['MWX', 'MWG', 'MWL'])
RNA = set(['RNA', 'RNL'])
HUMAN = PANELS | WHOLEGENOME - MICROBIAL - RNA | ANALYSIS_ONLY


class UnknownSequencingTypeError(Exception):
    pass


class ApplicationTag(str):

    def __init__(self, raw_tag):
        super(ApplicationTag, self).__init__()
        self = raw_tag

    @property
    def application(self):
        """Get the application part of the tag."""
        return self[0:3]

    @property
    def sequencing(self):
        """Get the library preparation part of the tag."""
        return self[:3]

    @property
    def library_prep(self):
        """Get the library preparation part of the tag."""
        return self[3:6]

    @property
    def is_human(self):
        """Determine if human sequencing."""
        return self.sequencing in HUMAN

    @property
    def is_panel(self):
        """Determine if sequencing if sequence capture."""
        return self.sequencing in PANELS

    @property
    def analysis_type(self):
        """Return analysis type from tag."""
        if self.sequencing.startswith('WG'):
            return 'wgs'
        elif self.sequencing in PANELS or self.sequencing.startswith('EX'):
            return 'wes'
        else:
            return None

    @property
    def is_microbial(self):
        """Determine if the order is for regular microbial samples."""
        return self.sequencing in MICROBIAL

    @property
    def sequencing_type(self):
        """parse application type to figure out type of sequencing."""
        if self.application in WHOLEGENOME:
            return 'wgs'
        elif self.application in PANELS:
            return 'wes'
        else:
            raise UnknownSequencingTypeError

    @property
    def is_external(self):
        """ Determines whether or not a sample is externally sequenced.

        Returns (bool): True when external, False otherwise
        """

        if self.sequencing.endswith('X'):
            return True
        return False

    @property
    def reads(self):
        """Calculate ordered number of reads."""
        type_id = self[-4]
        number = int(self[-3:])
        if type_id == 'R':
            return number * 1000000
        elif type_id == 'K':
            return number * 1000
        elif type_id == 'C':
            if self.is_panel:
                raise ValueError("can't convert coverage for panels")
            return number * 10000000 # but should be: number * READS_PER_1X
        else:
            raise ValueError("unknown read type id: {}".format(type_id))
