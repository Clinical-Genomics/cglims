# -*- coding: utf-8 -*-
from cglims import pedigree


def test_sequencing_type():
    # GIVEN a whole genome application tag
    app_tag = 'WGSPCFC030'
    # WHEN assessing the sequencing type
    seq_type = pedigree.sequencing_type(app_tag)
    # THEN it should come back as 'wgs'
    assert seq_type == 'wgs'
