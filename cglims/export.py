# -*- coding: utf-8 -*-
from datetime import datetime
import copy
import logging

import click
from dateutil.parser import parse as parse_date
import yaml

from cglims import api
from cglims.constants import SEX_MAP

log = logging.getLogger(__name__)


@click.command()
@click.argument('customer_or_case')
@click.argument('family_id', required=False)
@click.pass_context
def export(context, customer_or_case, family_id):
    """Parse out interesting data about a case."""
    lims = api.connect(context.obj)
    if family_id:
        customer = customer_or_case
    else:
        customer, family_id = customer_or_case.split('-', 1)
    lims_samples = lims.case(customer, family_id)
    case_data = export_case(lims, lims_samples)

    raw_dump = yaml.safe_dump(case_data, default_flow_style=False,
                              allow_unicode=True)
    click.echo(raw_dump)


def export_case(lims, lims_samples):
    """Gather data about a case, multiple samples in LIMS."""
    families = (get_familydata(lims_sample) for lims_sample in lims_samples)
    samples = []
    for lims_sample in lims_samples:
        artifacts = lims.get_artifacts(samplelimsid=lims_sample.id)
        data = sample_data(lims_sample, artifacts)
        samples.append(data)

    family_data = consolidate_family(families)
    family_data['samples'] = list(samples)
    return family_data


def get_familydata(lims_sample):
    """Parse out common (family-level) data."""
    data = {
        'customer': lims_sample.udf['customer'],
        'family_id': lims_sample.udf['familyID'],
        'case_id': "{}-{}".format(lims_sample.udf['customer'],
                                  lims_sample.udf['familyID']),
        'gene_panels': lims_sample.udf['Gene List'].split(';'),
        'reference_genome': lims_sample.udf['Reference Genome'],
    }
    return data


def sample_data(lims_sample, artifacts):
    """Parse out sample specific data."""
    capture_kit = lims_sample.udf.get('Capture Library version')
    try:
        data = {
            'id': lims_sample.id,
            'name': lims_sample.name,
            'received_at': parse_date(lims_sample.date_received),
            'status': lims_sample.udf['Status'].lower(),
            'delivery': lims_sample.udf['Data Analysis'],
            'sex': SEX_MAP.get(lims_sample.udf.get('Gender'), 'N/A'),
            'app_tag': lims_sample.udf['Sequencing Analysis'],
            'app_tag_version': int(lims_sample.udf.get('Application Tag Version', '1')),
            'priority': lims_sample.udf.get('priority', 'standard'),
            'capture_kit': capture_kit if capture_kit != 'NA' else None,
            'project': lims_sample.project.name,
        }
    except KeyError as error:
        log.error("missing UDF key for samples: %s", lims_sample.id)
        click.echo(lims_sample.udf.items(), err=True)
        raise error

    # parse artifacts
    for artifact in artifacts:
        if artifact.parent_process is None:
            continue
        elif artifact.parent_process.type.id == '33':
            process = artifact.parent_process
            data['capture_kit'] = process.udf['Capture Library version']
            data['library_prep_method'] = process.udf['Method document and version no:']
            data['library_prep_lotno'] = process.udf['Lot no: Capture library']
        elif artifact.parent_process.type.id == '667':
            # PCR Free library prep
            method_no = artifact.parent_process.udf['Method document']
            method_version = artifact.parent_process.udf['Method document version']
            data['library_prep_method'] = ":".join([method_no, method_version])
        elif artifact.parent_process.type.id == '663':
            # sequencing
            method_no = artifact.parent_process.udf['Method']
            method_version = artifact.parent_process.udf['Version']
            data['sequencing_method'] = ":".join([method_no, method_version])
            data['flowcell'] = artifact.parent_process.udf['Experiment Name']
        elif artifact.parent_process.type.id == '670':
            # more seq
            if 'Finish Date' in artifact.parent_process.udf:
                seq_date = artifact.parent_process.udf['Finish Date']
                data['sequencing_date'] = datetime.combine(seq_date, datetime.min.time())
            else:
                log.warn("sequencing date not found in LIMS: %s", lims_sample.id)
        elif artifact.parent_process.type.id == '159':
            # delivery
            delivery_date = artifact.parent_process.udf['Date delivered']
            data['delivery_date'] = datetime.combine(delivery_date, datetime.min.time())
            method_no = artifact.parent_process.udf['Method Document']
            method_version = artifact.parent_process.udf['Method Version']
            data['delivery_method'] = ':'.join([method_no, method_version])

    return data


def consolidate_family(families):
    """Consolidate family data across multiple samples."""
    for index, family in enumerate(families):
        if index == 0:
            new_data = copy.deepcopy(family)
            gene_panels = set(new_data['gene_panels'])

        else:
            assert family['customer'] == new_data['customer']
            assert family['family_id'] == new_data['family_id']
            assert family['reference_genome'] == new_data['reference_genome']
            for gene_panel in family['gene_panels']:
                gene_panels.add(gene_panel)

    new_data['gene_panels'] = list(gene_panels)

    return new_data
