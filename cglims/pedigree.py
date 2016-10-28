# -*- coding: utf-8 -*-
import logging

from .exc import MissingLimsDataException

SEX_MAP = dict(M='male', F='female', Unknown='unknown', unknown='unknown')
CAPTUREKIT_MAP = {'Agilent Sureselect CRE': 'Agilent_SureSelectCRE.V1',
                  'Agilent Sureselect V5': 'Agilent_SureSelect.V5', 'other' : 'Agilent_SureSelectCRE.V1'}
MANDATORY_HEADERS = ['Family ID', 'Individual ID', 'Paternal ID',
                     'Maternal ID', 'Sex', 'Phenotype']
EXTRA_HEADERS = ['Clinical_db', 'Capture_kit', 'display_name',
                 'Sequencing_type']

log = logging.getLogger(__name__)


def gather_data(lims_sample):
    """Gather analysis/pedigree data about a sample."""
    family_id = lims_sample.udf['familyID']
    app_tag = lims_sample.udf['Sequencing Analysis']
    sex_letter = lims_sample.udf['Gender']
    data = {
        'sample_id': get_sampleid(lims_sample),
        'sample_name': lims_sample.name,
        'sex': SEX_MAP[sex_letter],
        'phenotype': lims_sample.udf['Status'].lower(),
        'analysis_type': sequencing_type(app_tag),
        'expected_coverage': expected_coverage(app_tag),
    }
    for parent_field in ('fatherID', 'motherID'):
        parent_id = lims_sample.udf.get(parent_field)
        if parent_id and parent_id != '0':
            data[parent_field.replace('ID', '')] = parent_id
    return family_id, data


def expected_coverage(app_tag):
    """Parse out the expected coverage from the app tag."""
    read_part = app_tag[-4:]
    if read_part.startswith('C'):
        return int(read_part[1:])
    elif read_part.startswith('R'):
        # target reads expressed in millions
        return int(read_part[1:]) * 1.5
    else:
        raise ValueError("unexpected app tag: %s", app_tag)


def make_config(lims_api, customer, family_id, gene_panels=None,
                internalize=True):
    """Make the config for all samples."""
    lims_samples = lims_api.case(customer, family_id)
    active_samples = (lims_sample for lims_sample in lims_samples
                      if lims_sample.udf.get('cancelled') != 'yes')

    # filter out cancelled samples
    samples_data = []
    all_panels = set()
    for lims_sample in active_samples:
        sample_family_id, data = gather_data(lims_sample)
        assert sample_family_id == family_id, "non-matching family ids"

        # fetch capture kit if sample is exome sequenced
        if data['analysis_type'] == 'wes':
            data['capture_kit'] = capture_kit(lims_api, lims_sample)

        sample_panels = get_genepanels(lims_sample)
        for sample_panel in sample_panels:
            all_panels.add(sample_panel)

        samples_data.append(data)

    if internalize:
        samples_data = internalize_ids(samples_data)

    case_data = {
        'family_id': family_id,
        'gene_panels': gene_panels or list(all_panels),
        'samples': list(samples_data),
    }
    return case_data


def get_genepanels(lims_sample):
    try:
        genepanel_str = lims_sample.udf['Gene List']
        if ':' in genepanel_str:
            log.warn("wrong separator in 'Gene List': %s", genepanel_str)
            udf_key = 'Gene List'
            new_value = genepanel_str.replace(':', ';')
            lims_sample.udf[udf_key] = new_value
            log.info("updating %s: '%s' -> '%s'", lims_sample.id,
                     genepanel_str, new_value)
            lims_sample.put()
            genepanel_str = new_value
    except KeyError:
        message = "{}: 'Gene List'".format(lims_sample.id)
        raise MissingLimsDataException(message)
    return genepanel_str.split(';')


class UnknownSequencingTypeError(Exception):
    pass


def get_sampleid(lims_sample, key='Clinical Genomics ID'):
    """Get the expected LIMS or Clinical Genomics ID."""
    return lims_sample.udf.get(key) or lims_sample.id


def sequencing_type(app_tag):
    """Parse application type to figure out type of sequencing."""
    if app_tag.startswith('WG'):
        return 'wgs'
    elif app_tag.startswith('EX'):
        return 'wes'
    else:
        raise UnknownSequencingTypeError(app_tag)


def capture_kit(lims, lims_sample, udf_key='Capture Library version',
                udf_kitkey='Capture Library version'):
    """Figure out which capture kit has been used for the sample."""
    hybrizelib_id = '33'
    if udf_key in dict(lims_sample.udf.items()):
        log.debug('prefer capture kit annotated on the sample level')
        capture_kit = lims_sample.udf[udf_key]
    else:
        artifacts = lims.get_artifacts(samplelimsid=lims_sample.id,
                                       type='Analyte')
        capture_kit = None
        for artifact in artifacts:
            if artifact.parent_process:
                if artifact.parent_process.type.id == hybrizelib_id:
                    try:
                        capture_kit = artifact.parent_process.udf[udf_kitkey]
                    except KeyError:
                        log.warn('capture kit not found on expected process')
                        continue
                    break

        if capture_kit is None:
            raise MissingLimsDataException("No capture kit annotated: {}"
                                           .format(lims_sample.id))

    return CAPTUREKIT_MAP[capture_kit.strip()]


def internalize_ids(samples):
    """Replace customer sample ids with internal ids."""
    sample_map = {sample['sample_name']: sample for sample in samples}
    for external_id, sample_data in sample_map.items():
        parent_fields = ['father', 'mother']
        for parent_field in parent_fields:
            parent_id = sample_data.get('parent_field')
            if parent_id and parent_id != '0':
                sample_data[parent_field] = sample_map[parent_id]['sample_id']
        yield sample_data
