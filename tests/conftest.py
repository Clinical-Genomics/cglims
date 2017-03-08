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
def apptag_external():
    raw_tag = 'EXXCUSR000'
    return ApplicationTag(raw_tag)


@pytest.fixture
def apptags():
    return {
        'wgs': apptag_wgs(),
        'wes': apptag_wes(),
        'microbial': apptag_microbial(),
        'external': apptag_external()
    }

