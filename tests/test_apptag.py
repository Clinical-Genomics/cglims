# -*- coding: utf-8 -*-


def test_sequencing(apptag):
    # GIVEN a whole genome application tag
    # WHEN parsing sequencing type
    seq_type = apptag.sequencing
    # THEN is should reflect the type
    assert seq_type == 'WGS'

def test_sequencing_type(apptag):
    # WHEN assessing the sequencing type
    seq_type = apptag.sequencing_type
    # THEN it should come back as 'wgs'
    assert seq_type == 'wgs'
