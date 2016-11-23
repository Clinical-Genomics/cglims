# -*- coding: utf-8 -*-
from cglims.constants import READS_PER_1X

PANELS = ('EXO', 'EXT', 'MHP', 'EFT', 'CCP')
HISEQX = ('WGS', 'WGT', 'WGL', 'MWX')
ANALYSIS_ONLY = ('EXX', 'WGX')
MICROBIAL = ('MWX', 'MWG', 'MWL')
HUMAN = PANELS + HISEQX[:-1] + ANALYSIS_ONLY


class ApplicationTag(str):

    def __init__(self, raw_tag):
        super(ApplicationTag, self).__init__()
        self = raw_tag

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
    def is_microbial(self):
        """Determine if the order is for regular microbial samples."""
        return self.sequencing in MICROBIAL

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
            return number * READS_PER_1X
        else:
            raise ValueError("unknown read type id: {}".format(type_id))
