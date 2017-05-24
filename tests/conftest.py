# -*- coding: utf-8 -*-
import pytest

from cglims.api import ApplicationTag, Sample


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
        'external': apptag_external(),
        'external_wgs': apptag_external_wgs(),
        'metagenome': apptag_metagenome(),
        'rml': apptag_rml(),
        'targeted': apptag_focused_exome()
    }


@pytest.fixture
def sample_obj():
    _sample_obj = Sample()
    sample_id = 'SVE2300A5'
    sample_name = '17010-I-1A'
    udfs = {
        'Application Tag Version': '1',
        'Capture Library version': 'NA',
        'Concentration (nM)': 'NA',
        'Data Analysis': 'scout',
        'Gender': 'M',
        'Gene List': 'EP',
        'Index number': 'NA',
        'Index type': 'NA',
        'Passed Sequencing QC': 'False',
        'Process only if QC OK': 'yes',
        'Reads missing (M)': 0,
        'Reference Genome': 'hg19',
        'Reference Genome Microbial': 'NA',
        'Sample Buffer': 'NA',
        'Sequencing Analysis': 'WGTPCFC030',
        'Source': 'blood',
        'Status': 'affected',
        'Strain': 'NA',
        'Total Reads (M)': 882.716858,
        'Volume (uL)': 'NA',
        'customer': 'cust003',
        'familyID': '17010',
        'fatherID': '17010-II-1U',
        'motherID': '17010-II-2U',
        'pool name': 'NA',
        'priority': 'standard',
    }
    _sample_obj._parse_data(sample_id, sample_name, udfs)
    return _sample_obj
