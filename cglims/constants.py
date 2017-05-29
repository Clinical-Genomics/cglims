# -*- coding: utf-8 -*-
from __future__ import division

# for WGS, how many reads needed to cover genome 1x => reads to aim for!
TOTAL_COVERAGE = 30
READS_PER_HISEQ_X_LANE = 650000000
LOWEST_EXPECTED_YIELD = 0.75
READS_PER_1X = READS_PER_HISEQ_X_LANE / LOWEST_EXPECTED_YIELD / TOTAL_COVERAGE
SEX_MAP = {'F': 'female', 'M': 'male', 'Unknown': 'unknown', 'unknown': 'unknown'}
REV_SEX_MAP = {value: key for key, value in SEX_MAP.items()}
