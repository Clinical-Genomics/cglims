# -*- coding: utf-8 -*-
import logging

from cglims.exc import MissingLimsDataException
from cglims.api import Sample
from cglims.panels import convert_panels

SEX_MAP = dict(M='male', F='female', Unknown='unknown', unknown='unknown')
CAPTUREKIT_MAP = {'Agilent Sureselect CRE': 'Agilent_SureSelectCRE.V1',
                  'SureSelect CRE': 'Agilent_SureSelectCRE.V1',
                  'Agilent Sureselect V5': 'Agilent_SureSelect.V5',
                  'SureSelect Focused Exome': 'Agilent_SureSelectFocusedExome.V1',
                  'other': 'Agilent_SureSelectCRE.V1'}
LATEST_CAPTUREKIT = 'Agilent Sureselect CRE'

log = logging.getLogger(__name__)


class AnalysisConfig(object):

    """Utility to generate an analysis config for MIP.

    Args:
        lims_api (cglims.api.ClinicalLims): LIMS connection object
    """

    def __init__(self, lims_api):
        self.lims = lims_api
        self.customer_id = None
        self.family_name = None

    def __call__(self, customer_id, family_name):
        """Generate an analysis config for a case.

        Args:
            customer_id (str): customer id
            family_name (str): external family name

        Returns:
            dict: config values ready YAML dump
        """
        log.debug('fetch samples from LIMS')
        samples = self._get_samples(customer_id, family_name)
        log.debug('transform LIMS data needed for config')
        config_data = self._transform(samples)
        log.debug('validate input to config render function')
        self._validate(config_data)
        log.debug('render config object')
        config_obj = self._render(config_data)
        return config_obj

    def _get_samples(self, customer_id, family_name):
        """Get sample information from LIMS."""
        lims_samples = self.lims.case(customer_id, family_name)
        for lims_sample in lims_samples:
            sample_obj = Sample(lims_sample)
            if sample_obj.to_analysis:
                log.info("include sample: %s", sample_obj['id'])
                if sample_obj.apptag.sequencing_type_mip == 'wes':
                    # we need a capture kit
                    sample_obj['capture_kit'] = self.get_capture_kit(sample_obj)
                yield sample_obj

    def get_capture_kit(self, sample_obj):
        """Figure out which capture kit has been used for the sample."""
        udf_kit_key = 'SureSelect capture library/libraries used'
        udf_key = 'Capture Library version'
        sample_capture_kit = sample_obj.get(udf_key)
        if sample_capture_kit and sample_capture_kit != 'NA':
            log.debug('found manually added capture kit')
            return sample_capture_kit
        else:
            artifacts = self.lims.get_artifacts(samplelimsid=sample_obj['id'], type='Analyte',
                                                process_type='CG002 - Hybridize Library  (SS XT)')
            capture_kit = None
            for artifact in artifacts:
                try:
                    capture_kit = artifact.parent_process.udf[udf_kit_key]
                except KeyError:
                    log.warning('capture kit not found on expected process')
                    continue
                break

            if capture_kit is None:
                raise MissingLimsDataException("No capture kit: {}".format(sample_obj['id']))
        return capture_kit.strip()

    @classmethod
    def _transform(cls, samples):
        """Format sample data for config generation."""
        config_data = {'customer': set(), 'family_name': set(), 'default_panels': set(),
                       'samples': []}
        for sample_obj in samples:
            customer, family_name, sample_data = cls._transform_sample(sample_obj)
            config_data['customer'].add(customer)
            config_data['family_name'].add(family_name)
            config_data['samples'].append(sample_data)
            for panel_id in sample_obj['panels']:
                config_data['default_panels'].add(panel_id)

        # Convert external sample references to internal ids
        cls._internalize_ids(config_data['samples'])

        # MIP can't handle single samples with 'unknown' phenotype
        if len(config_data['samples']) == 1:
            if config_data['samples'][0]['phenotype'] == 'unknown':
                sample_id = config_data['samples'][0]['id']
                log.warning("setting unknown phenotype to 'unaffected': %s", sample_id)
                config_data['samples'][0]['phenotype'] = 'unaffected'

        assert len(config_data['customer']) == 1, 'multiple customers'
        config_data['customer'] = config_data['customer'].pop()
        assert len(config_data['family_name']) == 1, 'multiple family names'
        config_data['family_name'] = config_data['family_name'].pop()

        # convert default panels into full set of gene panels
        config_data['default_panels'] = list(config_data['default_panels'])
        config_data['panels'] = list(convert_panels(config_data['customer'],
                                                    config_data['default_panels']))
        return config_data

    @staticmethod
    def _internalize_ids(samples_data):
        """Convert parent sample references to internal IDs."""
        # internalize sample id's in sample relationships
        sample_map = {sample['sample_name']: sample['sample_id'] for sample in samples_data}
        for sample_data in samples_data:
            for parent_field in ['father', 'mother']:
                parent_sample = sample_data.get(parent_field)
                if parent_sample:
                    if parent_sample not in sample_map:
                        message = "Missing reference: {} - {}".format(parent_field, parent_sample)
                        raise MissingLimsDataException(message)
                    sample_data[parent_field] = sample_map[parent_sample]

    @staticmethod
    def _transform_sample(sample_obj):
        """Format data for a single sample."""
        customer = sample_obj['customer']
        family_name = sample_obj['familyID']
        sample_data = {
            'sample_id': sample_obj['old_id'] or sample_obj['id'],
            'sample_name': sample_obj['name'],
            'sex': sample_obj['sex'],
            'phenotype': sample_obj['Status'],
            'analysis_type': sample_obj.apptag.sequencing_type_mip,
            'expected_coverage': sample_obj.apptag.expected_coverage,
        }

        if sample_data['analysis_type'] == 'wgs':
            # fill in a default capture kit for coverage analysis
            sample_data['capture_kit'] = LATEST_CAPTUREKIT

        for parent_field in ('fatherID', 'motherID'):
            parent_id = sample_obj.get(parent_field)
            if parent_id and parent_id != '0':
                sample_data[parent_field.replace('ID', '')] = parent_id

        return customer, family_name, sample_data

    @staticmethod
    def _validate(config_data):
        """Validate that config data is correct."""
        samples_data = config_data['samples']
        sexes = {sample['sample_id']: sample['sex'] for sample in samples_data}
        for sample_data in samples_data:
            for parent_key, expected_sex in [('father', 'male'), ('mother', 'female')]:
                parent_id = sample_data.get(parent_key)
                if parent_id:
                    if sexes[parent_id] != expected_sex:
                        sex = sexes[parent_id]
                        raise ValueError("%s sex incorrect: %s, %s", parent_key, parent_id, sex)

    @staticmethod
    def _render(config_data):
        """Render an analysis config from input config data."""
        config_obj = {
            'owner': config_data['customer'],
            'family': config_data['family_name'],
            'default_gene_panels': config_data['default_panels'],
            'gene_panels': config_data['panels'],
            'samples': [],
        }
        for sample_data in config_data['samples']:
            config_obj['samples'].append({
                'sample_id': sample_data['sample_id'],
                'sample_name': sample_data['sample_name'],
                'sex': sample_data['sex'],
                'analysis_type': sample_data['analysis_type'],
                'expected_coverage': sample_data['expected_coverage'],
                'mother': sample_data.get('mother', '0'),
                'father': sample_data.get('father', '0'),
                'capture_kit': CAPTUREKIT_MAP[sample_data['capture_kit']],
            })
        return config_obj
