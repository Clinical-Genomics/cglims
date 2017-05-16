# -*- coding: utf-8 -*-
import pytest
from cglims.apptag import UnknownSequencingTypeError


def test_application(apptags):
    # GIVEN a application tag
    # WHEN parsing sequencing type
    # THEN is should reflect the type
    for apptag_type, apptag in apptags.iteritems():
        app_type = apptag.application
        if apptag_type == 'wgs':
            assert app_type == 'WGS'
        if apptag_type == 'wes':
            assert app_type == 'EXO'
        if apptag_type == 'microbial':
            assert app_type == 'MWG'
        if apptag_type == 'external':
            assert app_type == 'EXX'
        if apptag_type == 'metagenome':
            assert app_type == 'MET'
        if apptag_type == 'rml':
            assert app_type == 'RML'

def test_sequencing_type(apptags):
    for apptag_type, apptag in apptags.iteritems():
        if apptag_type == 'rml':
            with pytest.raises(UnknownSequencingTypeError):
                seq_type = apptag.sequencing_type
        else:
            seq_type = apptag.sequencing_type
        if apptag_type == 'wgs':
            assert seq_type == 'wgs'
        if apptag_type == 'wes':
            assert seq_type == 'wes'
        if apptag_type == 'external':
            assert seq_type == 'wes'
        if apptag_type == 'metagenome':
            assert seq_type == 'wgs'
        if apptag_type == 'microbial':
            assert seq_type == 'wgs'

def test_library_prep(apptags):
    for apptag_type, apptag in apptags.iteritems():
        lib_prep = apptag.library_prep
        if apptag_type == 'wgs':
            assert lib_prep == 'PCF'
        if apptag_type == 'wes':
            assert lib_prep == 'SXT'
        if apptag_type == 'microbial':
            assert lib_prep == 'NXT'
        if apptag_type == 'external':
            assert lib_prep == 'CUS'
        if apptag_type == 'metagenome':
            assert lib_prep == 'PCF'
        if apptag_type == 'rml':
            assert lib_prep == 'P10'

def test_is_human(apptags):
    for apptag_type, apptag in apptags.iteritems():
        is_human = apptag.is_human
        if apptag_type == 'wgs':
            assert is_human == True
        if apptag_type == 'wes':
            assert is_human == True
        if apptag_type == 'microbial':
            assert is_human == False
        if apptag_type == 'external':
            assert is_human == True
        if apptag_type == 'metagenome':
            assert is_human == True
        if apptag_type == 'rml':
            assert is_human == False

def test_is_panel(apptags):
    for apptag_type, apptag in apptags.iteritems():
        is_panel = apptag.is_panel
        if apptag_type == 'wgs':
            assert is_panel == False
        if apptag_type == 'wes':
            assert is_panel == True
        if apptag_type == 'microbial':
            assert is_panel == False
        if apptag_type == 'external':
            assert is_panel == True
        if apptag_type == 'metagenome':
            assert is_panel == False
        if apptag_type == 'rml':
            assert is_panel == False

def test_analysis_type(apptags):
    for apptag_type, apptag in apptags.iteritems():
        analysis_type = apptag.analysis_type
        if apptag_type == 'wgs':
            assert analysis_type == 'wgs'
        if apptag_type == 'wes':
            assert analysis_type == 'wes'
        if apptag_type == 'microbial':
            assert analysis_type == None
        if apptag_type == 'external':
            assert analysis_type == 'wes'
        if apptag_type == 'metagenome':
            assert analysis_type == None
        if apptag_type == 'rml':
            assert analysis_type == None

def test_is_microbial(apptags):
    for apptag_type, apptag in apptags.iteritems():
        is_microbial = apptag.is_microbial
        if apptag_type == 'wgs':
            assert is_microbial == False
        if apptag_type == 'wes':
            assert is_microbial == False
        if apptag_type == 'microbial':
            assert is_microbial == True
        if apptag_type == 'external':
            assert is_microbial == False
        if apptag_type == 'metagenome':
            assert is_microbial == False
        if apptag_type == 'rml':
            assert is_microbial == False

def test_is_external(apptags):
    for apptag_type, apptag in apptags.iteritems():
        is_external = apptag.is_external
        if apptag_type == 'wgs':
            assert is_external == False
        if apptag_type == 'wes':
            assert is_external == False
        if apptag_type == 'microbial':
            assert is_external == False
        if apptag_type == 'external':
            assert is_external == True
        if apptag_type == 'metagenome':
            assert is_external == False
        if apptag_type == 'rml':
            assert is_external == False

def test_reads(apptags):
    for apptag_type, apptag in apptags.iteritems():
        reads = apptag.reads
        if apptag_type == 'wgs':
            assert reads == 10000000 * 30
        if apptag_type == 'wes':
            assert reads == 100000000
        if apptag_type == 'microbial':
            assert reads == 3000000
        if apptag_type == 'external':
            assert reads == 0
        if apptag_type == 'metagenome':
            assert reads == 20000000
        if apptag_type == 'rml':
            assert reads == 150000000
