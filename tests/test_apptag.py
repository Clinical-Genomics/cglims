# -*- coding: utf-8 -*-


def test_sequencing(apptag):
    # GIVEN a whole genome application tag
    # WHEN parsing sequencing type
    seq_type = apptag.sequencing
    # THEN is should reflect the type
    assert seq_type == 'WGS'
