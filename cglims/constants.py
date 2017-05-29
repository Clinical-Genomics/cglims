# -*- coding: utf-8 -*-
from __future__ import division

# for WGS, how many reads needed to cover genome 1x => reads to aim for!
TOTAL_COVERAGE = 30
READS_PER_HISEQ_X_LANE = 650000000
LOWEST_EXPECTED_YIELD = 0.75
READS_PER_1X = READS_PER_HISEQ_X_LANE / LOWEST_EXPECTED_YIELD / TOTAL_COVERAGE
SEX_MAP = dict(M='male', F='female', Unknown='unknown', unknown='unknown')
REV_SEX_MAP = {value: key for key, value in SEX_MAP.items()}
CAPTUREKIT_MAP = {'Agilent Sureselect CRE': 'Agilent_SureSelectCRE.V1',
                  'SureSelect CRE': 'Agilent_SureSelectCRE.V1',
                  'Agilent Sureselect V5': 'Agilent_SureSelect.V5',
                  'SureSelect Focused Exome': 'Agilent_SureSelectFocusedExome.V1',
                  'other': 'Agilent_SureSelectCRE.V1'}
LATEST_CAPTUREKIT = 'Agilent Sureselect CRE'
