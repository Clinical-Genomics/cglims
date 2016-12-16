# -*- coding: utf-8 -*-
import logging
import io
import copy
import csv

from .config import capture_kit, CAPTUREKIT_MAP
from .exc import MissingLimsDataException


PHENOTYPE_MAP = dict(affected='2', unaffected='1', unknown='0')
SEX_MAP = dict(M='1', F='2', Unknown='other', unknown='other')
MANDATORY_HEADERS = ['Family ID', 'Individual ID', 'Paternal ID',
                     'Maternal ID', 'Sex', 'Phenotype']
EXTRA_HEADERS = ['Clinical_db', 'Capture_kit', 'display_name',
                 'Sequencing_type']

log = logging.getLogger(__name__)


class UnknownSequencingTypeError(Exception):
    pass


def get_sampleid(lims_sample, key='Clinical Genomics ID'):
    """Get the expected LIMS or Clinical Genomics ID."""
    return lims_sample.udf.get(key) or lims_sample.id


def sequencing_type(app_tag):
    """Parse application type to figure out type of sequencing."""
    if app_tag.startswith('WG'):
        return 'wgs'
    elif app_tag.startswith('EX') or app_tag.startswith('EFT'):
        return 'wes'
    else:
        raise UnknownSequencingTypeError(app_tag)


def old_capture_kit(lims, lims_sample, udf_key='Capture Library version',
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


def make_pedigree(api, lims_samples, family_id=None, gene_panel=None,
                  internalize=True):
    """String together all individual steps to create a pedigree."""
    # extract information about samples
    samples = [convert_sample(api, lims_sample, gene_panel=gene_panel)
               for lims_sample in lims_samples
               if lims_sample.udf.get('cancelled') != 'yes']
    if internalize:
        samples = internalize_ids(samples)
    if family_id:
        raw_samples = samples
        samples = []
        for sample in raw_samples:
            sample['Family ID'] = family_id
            samples.append(sample)
    # serialize to CSV PED file
    rows = serialize(samples)
    return "#{}".format(rows)


def convert_sample(api, lims_sample, gene_panel=None):
    """Extract information from LIMS samples that relate to pedigree."""
    app_tag = lims_sample.udf['Sequencing Analysis']
    affection_status = lims_sample.udf['Status'].lower()
    sex_letter = lims_sample.udf['Gender']
    if gene_panel:
        gene_panels = gene_panel
    else:
        try:
            gene_panels = lims_sample.udf['Gene List']
            if ':' in gene_panels:
                log.warn("wrong separator in 'Gene List': %s", gene_panels)
                udf_key = 'Gene List'
                new_value = gene_panels.replace(':', ';')
                lims_sample.udf[udf_key] = new_value
                log.info("updating %s: '%s' -> '%s'", lims_sample.id,
                         gene_panels, new_value)
                lims_sample.put()
                gene_panels = new_value
        except KeyError:
            message = "{}: 'Gene List'".format(lims_sample.id)
            raise MissingLimsDataException(message)
    try:
        ped_phenotype = PHENOTYPE_MAP[affection_status]
    except KeyError:
        msg = "{}: 'Status' -> '{}'".format(lims_sample.id, affection_status)
        raise MissingLimsDataException(msg)
    data = {
        'Family ID': lims_sample.udf['familyID'],
        'Individual ID': lims_sample.name,
        'Paternal ID': lims_sample.udf.get('fatherID', '0'),
        'Maternal ID': lims_sample.udf.get('motherID', '0'),
        'Sex': SEX_MAP[sex_letter],
        'Phenotype': ped_phenotype,
        'Clinical_db': gene_panels,
        'Sequencing_type': sequencing_type(app_tag),
        'internal_id': get_sampleid(lims_sample),
    }

    # fetch capture kit if sample is exome sequenced
    if data['Sequencing_type'] == 'wes':
        data['Capture_kit'] = capture_kit(api, lims_sample)
    else:
        data['Capture_kit'] = None

    return data


def internalize_ids(samples):
    """Replace customer sample ids with internal ids."""
    sample_map = {sample['Individual ID']: sample for sample in samples}
    for external_id, sample in sample_map.items():
        new_sample = copy.deepcopy(sample)
        new_sample['Individual ID'] = sample['internal_id']
        new_sample['display_name'] = external_id

        parent_fields = ['Paternal ID', 'Maternal ID']
        for parent_field in parent_fields:
            parent_id = new_sample[parent_field]
            if parent_id != '0':
                new_sample[parent_field] = sample_map[parent_id]['internal_id']
        yield new_sample


def serialize(sample_dicts, headers=None, extra=None):
    """Serialize a list of samples into PED output to a file.

    Args:
        sample_dicts (List[dict]): list of dicts with values
        headers (Optional[list]): order of headers to output
    """
    output = io.BytesIO()
    headers = headers or MANDATORY_HEADERS
    extra = extra or EXTRA_HEADERS
    all_headers = headers + extra
    dict_writer = csv.DictWriter(output, all_headers, extrasaction='ignore',
                                 dialect='excel-tab', lineterminator='\n')
    dict_writer.writeheader()
    dict_writer.writerows(sample_dicts)
    return output.getvalue()
