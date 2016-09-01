# -*- coding: utf-8 -*-
import io
import copy
import csv

PHENOTYPE_MAP = dict(Affected='2', Unaffected='1', unknown='0')
SEX_MAP = dict(M='1', F='2')


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


def make_pedigree(api, customer, family_id, internalize=True):
    """String together all individual steps to create a pedigree."""
    # find sample in lims
    lims_samples = api.case(customer, family_id)
    # extract information about samples
    samples = [convert_sample(lims_sample) for lims_sample in lims_samples
               if lims_sample.udf.get('cancelled') != 'yes']
    if internalize:
        samples = internalize_ids(samples)
    # serialize to CSV PED file
    rows = serialize(samples)
    return "#{}".format(rows)


def convert_sample(lims_sample):
    """Extract information from LIMS samples that relate to pedigree."""
    app_tag = lims_sample.udf['Sequencing Analysis']
    affection_status = lims_sample.udf['Status']
    sex_letter = lims_sample.udf['Gender']
    data = {
        'Family ID': lims_sample.udf['familyID'],
        'Individual ID': lims_sample.name,
        'Paternal ID': lims_sample.udf.get('fatherID', '0'),
        'Maternal ID': lims_sample.udf.get('motherID', '0'),
        'Sex': SEX_MAP[sex_letter],
        'Phenotype': PHENOTYPE_MAP[affection_status],
        'Clinical_db': lims_sample.udf['Gene List'],
        'Sequencing_type': sequencing_type(app_tag),
        'internal_id': get_sampleid(lims_sample),
    }
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
    headers = headers or ['Family ID', 'Individual ID', 'Paternal ID',
                          'Maternal ID', 'Sex', 'Phenotype']
    extra = extra or ['Clinical_db', 'display_name', 'Sequencing_type']
    all_headers = headers + extra
    dict_writer = csv.DictWriter(output, all_headers, extrasaction='ignore',
                                 dialect='excel-tab', lineterminator='\n')
    dict_writer.writeheader()
    dict_writer.writerows(sample_dicts)
    return output.getvalue()
