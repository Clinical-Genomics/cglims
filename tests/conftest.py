# -*- coding: utf-8 -*-
import pytest

from cglims.apptag import ApplicationTag


@pytest.fixture
def apptag_wgs():
    raw_tag = 'WGSPCFC030'
    return ApplicationTag(raw_tag)


@pytest.fixture
def apptag_wes():
    raw_tag = 'EXOSXTR100'
    return ApplicationTag(raw_tag)


@pytest.fixture
def apptag_microbial():
    raw_tag = 'MWGNXTR003'
    return ApplicationTag(raw_tag)


@pytest.fixture
def apptag_rna():
    raw_tag = 'RNLPOAR030'
    return ApplicationTag(raw_tag)


@pytest.fixture
def apptag_external():
    raw_tag = 'EXXCUSR000'
    return ApplicationTag(raw_tag)


@pytest.fixture
def apptag_external_wgs():
    raw_tag = 'WGXCUSR000'
    return ApplicationTag(raw_tag)


@pytest.fixture
def apptag_metagenome():
    raw_tag = 'METPCFR020'
    return ApplicationTag(raw_tag)


@pytest.fixture
def apptag_rml():
    raw_tag = 'RMLP10R150'
    return ApplicationTag(raw_tag)


@pytest.fixture
def apptag_focused_exome():
    raw_tag = 'EFTSXTR020'
    return ApplicationTag(raw_tag)


@pytest.fixture
def apptags():
    return {
        'wgs': apptag_wgs(),
        'wes': apptag_wes(),
        'microbial': apptag_microbial(),
        'rna': apptag_rna(),
        'external': apptag_external(),
        'external_wgs': apptag_external_wgs(),
        'metagenome': apptag_metagenome(),
        'rml': apptag_rml(),
        'targeted': apptag_focused_exome()
    }

