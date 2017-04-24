# -*- coding: utf-8 -*-

from cglims.api import SamplesheetHandler

def test_samplesheet():
    samplesheethandler = SamplesheetHandler()

    assert samplesheethandler._get_placement_lane('4:1') == 4
#    assert samplesheethandler._get_index('G07 - D707-D507 (CTGAAGCT-CAGGACGT)') == 'CTGAAGCT-CAGGACGT'
