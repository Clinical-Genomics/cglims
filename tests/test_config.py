# -*- coding: utf-8 -*-
from cglims.config import AnalysisConfig


def test_internalize_ids():
    # GIVEN simple family with external sample name references
    mother_sample = {'sample_id': 'internal2', 'sample_name': 'external2'}
    father_sample = {'sample_id': 'internal3', 'sample_name': 'external3'}
    child_sample = {'sample_id': 'internal1', 'sample_name': 'external1',
                    'mother': mother_sample['sample_name'], 'father': father_sample['sample_name']}
    samples_data = [child_sample, mother_sample, father_sample]
    assert child_sample['mother'] == mother_sample['sample_name']
    assert child_sample['father'] == father_sample['sample_name']
    # WHEN internalizing parental sample references
    AnalysisConfig._internalize_ids(samples_data)
    # THEN the child sample should have references to internal ids
    assert child_sample['mother'] == mother_sample['sample_id']
    assert child_sample['father'] == father_sample['sample_id']


def test_transform_sample_with_parents(sample_obj):
    # GIVEN a regular sample with parent references
    assert sample_obj['motherID'] != '0'
    assert sample_obj['fatherID'] != '0'
    # WHEN transforming data for the config
    _, _, sample_data = AnalysisConfig._transform_sample(sample_obj)
    # THEN it should fill in correct relationships
    assert sample_data['mother'] == sample_obj['motherID']
    assert sample_data['father'] == sample_obj['fatherID']
