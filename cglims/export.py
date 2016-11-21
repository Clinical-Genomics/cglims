# -*- coding: utf-8 -*-
import copy
import logging

import click
from dateutil.parser import parse as parse_date
import yaml

from cglims import api

log = logging.getLogger(__name__)


@click.command()
@click.argument('customer')
@click.argument('family_id')
@click.pass_context
def export(context, customer, family_id):
    """Parse out interesting data about a case."""
    lims = api.connect(context.obj)
    lims_samples = lims.case(customer, family_id)
    case_data = export_case(lims_samples)

    raw_dump = yaml.safe_dump(case_data, default_flow_style=False,
                              allow_unicode=True)
    click.echo(raw_dump)


def export_case(lims_samples):
    """Gather data about a case, multiple samples in LIMS."""
    families = (family_data(lims_sample) for lims_sample in lims_samples)
    samples = (sample_data(lims_sample) for lims_sample in lims_samples)

    data = consolidate_family(families)
    data['samples'] = list(samples)
    return data


def family_data(lims_sample):
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


def sample_data(lims_sample):
    """Parse out sample specific data."""
    capture_kit = lims_sample.udf.get('Capture Library version')
    try:
        data = {
            'id': lims_sample.id,
            'name': lims_sample.name,
            'received_at': parse_date(lims_sample.date_received),
            'status': lims_sample.udf['Status'],
            'delivery': lims_sample.udf['Data Analysis'],
            'sex': lims_sample.udf['Gender'],
            'app_tag': lims_sample.udf['Sequencing Analysis'],
            'priority': lims_sample.udf.get('priority', 'standard'),
            'capture_kit': capture_kit if capture_kit != 'NA' else None,
        }
    except KeyError as error:
        log.error("missing UDF key for samples: %s", lims_sample.id)
        click.echo(lims_sample.udf.items(), err=True)
        raise error

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
