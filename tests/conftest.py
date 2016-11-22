# -*- coding: utf-8 -*-
import pytest

from cglims.apptag import ApplicationTag


@pytest.fixture
def apptag():
    raw_tag = 'WGSPCFC030'
    return ApplicationTag(raw_tag)
