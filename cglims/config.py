# -*- coding: utf-8 -*-
import logging

from .exc import MissingLimsDataException
from .apptag import ApplicationTag
from .panels import convert_panels

SEX_MAP = dict(M='male', F='female', Unknown='unknown', unknown='unknown')
CAPTUREKIT_MAP = {'Agilent Sureselect CRE': 'Agilent_SureSelectCRE.V1',
                  'SureSelect CRE': 'Agilent_SureSelectCRE.V1',
                  'Agilent Sureselect V5': 'Agilent_SureSelect.V5',
                  'SureSelect Focused Exome': 'Agilent_SureSelectFocusedExome.V1',
                  'other': 'Agilent_SureSelectCRE.V1'}
LATEST_CAPTUREKIT = 'Agilent_SureSelectCRE.V1'

log = logging.getLogger(__name__)


def relevant_samples(lims_samples):
    """Filter out relevant samples for analysis."""
    included = (lims_sample for lims_sample in lims_samples
                if (lims_sample.udf.get('cancelled') != 'yes' and
                    lims_sample.udf.get('tumor') != 'yes' and
                    lims_sample.udf.get('exclude analysis') != 'yes'))
    return included


def basic_config(lims_api, customer_id, family_id):
    """Generate data for a basic config."""
    lims_samples = lims_api.case(customer_id, family_id)
    included_samples = relevant_samples(lims_samples)
    data = make_config(lims_api, included_samples, family_id=family_id)
    # handle single sample cases with 'unknown' phenotype
    if len(data['samples']) == 1:
        if data['samples'][0]['phenotype'] == 'unknown':
            log.info("setting 'unknown' phenotype to 'unaffected'")
            data['samples'][0]['phenotype'] = 'unaffected'
    return data


def gather_data(lims_sample):
    """Gather analysis/pedigree data about a sample."""
    customer = lims_sample.udf['customer']
    family_id = lims_sample.udf['familyID']
    sex_letter = lims_sample.udf['Gender']
    app_tag = ApplicationTag(lims_sample.udf['Sequencing Analysis'])

    data = {
        'sample_id': get_sampleid(lims_sample),
        'sample_name': lims_sample.name,
        'sex': SEX_MAP[sex_letter],
        'phenotype': lims_sample.udf['Status'].lower(),
        'analysis_type': app_tag.sequencing_type_mip,
        'expected_coverage': expected_coverage(app_tag),
    }
    for parent_field in ('fatherID', 'motherID'):
        parent_id = lims_sample.udf.get(parent_field)
        if parent_id and parent_id != '0':
            data[parent_field.replace('ID', '')] = parent_id
    return customer, family_id, data


def expected_coverage(app_tag):
    """Parse out the expected coverage from the app tag."""
    read_part = app_tag[-4:]
    if read_part.startswith('C'):
        return int(read_part[1:]) * 0.87
    elif read_part.startswith('R'):
        # target reads expressed in millions
        return int(read_part[1:]) * 1.5 * 0.87
    else:
        raise ValueError("unexpected app tag: %s", app_tag)


def make_config(lims_api, lims_samples, customer=None, family_id=None,
                gene_panels=None, capture_kit=None, force=False):
    """Make the config for all samples."""
    samples_data = []
    customers = set()
    families = set()
    all_panels = set()
    for lims_sample in lims_samples:
        sample_customer, sample_family, data = gather_data(lims_sample)
        customers.add(sample_customer)
        families.add(sample_family)

        # fetch capture kit if sample is exome sequenced
        if data['analysis_type'] == 'wes':
            data['capture_kit'] = capture_kit or get_capture_kit(lims_api, lims_sample)
        else:
            # wgs: just fill in a default capture kit for coverage analysis
            data['capture_kit'] = LATEST_CAPTUREKIT

        sample_panels = get_genepanels(lims_sample)
        for sample_panel in sample_panels:
            all_panels.add(sample_panel)

        # add mandatory columns
        data['father'] = data.get('father', 0)
        data['mother'] = data.get('mother', 0)

        samples_data.append(data)

    samples_data = list(internalize_ids(samples_data))
    if not force:
        check_relations(samples_data)

    if customer is None:
        assert len(customers) == 1, "conflicting custs: {}".format(customers)
        customer = customers.pop()
    if family_id is None:
        assert len(families) == 1, "conflicting families: {}".format(families)
        family_id = families.pop()

    gene_panels = gene_panels or list(all_panels)
    case_data = {
        'owner': customer,
        'family': family_id,
        'default_gene_panels': gene_panels,
        'gene_panels': convert_panels(customer, gene_panels),
        'samples': samples_data,
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

    gene_panels = set(gene_panel.strip() for gene_panel in genepanel_str.split(';'))
    additional = lims_sample.udf.get('Additional Gene List')
    if additional:
        gene_panels.add(additional.strip())

    return list(gene_panels)


def get_sampleid(lims_sample, key='Clinical Genomics ID'):
    """Get the expected LIMS or Clinical Genomics ID."""
    return lims_sample.udf.get(key) or lims_sample.id


def get_capture_kit(lims, lims_sample, udf_key='Capture Library version',
                    udf_kitkey='SureSelect capture library/libraries used'):
    """Figure out which capture kit has been used for the sample."""
    hybrizelib_id = '669'
    udfs = dict(lims_sample.udf.items())
    sample_capture_kit = udfs.get(udf_key)
    if sample_capture_kit and sample_capture_kit != 'NA':
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
            parent_id = sample_data.get(parent_field)
            if parent_id and parent_id != '0':
                sample_data[parent_field] = sample_map[parent_id]['sample_id']
        yield sample_data


def check_relations(samples):
    """Check parental relations between samples."""
    sexes = {sample['sample_id']: sample['sex'] for sample in samples}
    for sample in samples:
        if sample['father'] != 0:
            if sample['father'] not in sexes:
                raise ValueError("father not referenced: %s", sample['father'])
            elif sexes[sample['father']] != 'male':
                sex = sexes[sample['father']]
                raise ValueError("father sex incorrect: %s, %s", sample['father'], sex)

        if sample['mother'] != 0:
            if sample['mother'] not in sexes:
                raise ValueError("mother not referenced: %s", sample['mother'])
            elif sexes[sample['mother']] != 'female':
                sex = sexes[sample['mother']]
                raise ValueError("mother sex incorrect: %s, %s", sample['mother'], sex)
