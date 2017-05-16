# -*- coding: utf-8 -*-

import warnings

from cglims.constants import READS_PER_1X

PANELS = set(['EXO', 'EXT', 'MHP', 'EFT', 'CCP', 'EXX'])
WHOLEGENOME = set(['WGS', 'WGT', 'WGL', 'MWG', 'MWL', 'MWX', 'MET', 'MEL', 'WGX'])
ANALYSIS_ONLY = set(['EXX', 'WGX'])
MICROBIAL = set(['MWX', 'MWG', 'MWL'])
RNA = set(['RNA', 'RNL'])
HUMAN = (PANELS | WHOLEGENOME | ANALYSIS_ONLY) - MICROBIAL - RNA


class UnknownSequencingTypeError(Exception):
    pass


class ApplicationTag(str):

    def __init__(self, raw_tag):
        super(ApplicationTag, self).__init__()
        self = raw_tag

    @property
    def application(self):
        """Get the application part of the tag."""
        return self[:3]

    @property
    def sequencing(self):
        """DEPRICATED: replaced by application()."""
        warnings.warn('Deprecated: use application() instead', DeprecationWarning, stacklevel=2)
        return self[:3]

    @property
    def library_prep(self):
        """Get the library preparation part of the tag."""
        return self[3:6]

    @property
    def is_human(self):
        """Determine if human sequencing."""
        return self.application in HUMAN

    @property
    def is_panel(self):
        """Determine if sequencing if sequence capture."""
        return self.application in PANELS

    @property
    def analysis_type(self):
        """Return analysis type from tag."""
        warnings.warn('Deprecated: use sequencing_type() instead', DeprecationWarning, stacklevel=2)
        return self.sequencing_type()

    @property
    def category(self):
        """Return the category of application."""
        category = self.sequencing_type
        if self.is_external:
            category = "{}-ext".format(category)
        return category

    @property
    def is_microbial(self):
        """Determine if the order is for regular microbial samples."""
        return self.application in MICROBIAL

    @property
    def sequencing_type(self):
        """parse application type to figure out type of sequencing."""
        if self.application in WHOLEGENOME:
            return 'wgs'
        elif self.application in PANELS:
            return 'wes'
        elif self.sequencing in ('MHP', 'EFT', 'CCP'):
            return 'tga'
        else:
            raise UnknownSequencingTypeError

    @property
    def is_external(self):
        """ Determines whether or not a sample is externally sequenced.

        Returns (bool): True when external, False otherwise
        """

        if self.application.endswith('X'):
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
