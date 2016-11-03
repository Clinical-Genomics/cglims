# -*- coding: utf-8 -*-
from datetime import datetime
from copy import deepcopy

import click
import yaml

from cglims import api
from .utils import jsonify, fix_dump
from cglims.pedigree import make_config

SEX_MAP = {'F': 'female', 'M': 'male', 'Unknown': 'unknown'}


@click.command()
@click.option('-g', '--gene-panel', help='custom gene panel')
@click.argument('customer')
@click.argument('family')
@click.pass_context
def config(context, gene_panel, customer, family):
    """Create pedigree from LIMS."""
    lims_api = api.connect(context.obj)
    gene_panels = [gene_panel] if gene_panel else None
    family = family.encode('utf-8')
    data = make_config(lims_api, customer, family, gene_panels=gene_panels)
    dump = yaml.dump(data, default_flow_style=False, allow_unicode=True)
    click.echo(fix_dump(dump))


@click.command()
@click.option('-c', '--condense', is_flag=True, help='condense output')
@click.argument('identifier')
@click.argument('fields', nargs=-1, required=False)
@click.pass_context
def get(context, condense, identifier, fields):
    """Get information from LIMS: either sample or family samples."""
    lims = api.connect(context.obj)
    if identifier.startswith('cust'):
        # look up samples in a case
        samples = lims.case(*identifier.split('-', 1))
    else:
        # look up a single sample
        is_cgid = True if identifier[0].isdigit() else False
        samples = [lims.sample(identifier, is_cgid=is_cgid)]

    for sample in samples:
        values = deepcopy(sample.udf._lookup)
        values['id'] = sample.id
        values['name'] = sample.name
        date_parts = map(int, sample.date_received.split('-'))
        values['date_received'] = datetime(*date_parts)
        values['project_name'] = sample.project.name
        values['sex'] = SEX_MAP.get(values.get('Gender'), 'N/A')
        if 'customer' in values and 'familyID' in values:
            values['case_id'] = "{}-{}".format(values['customer'],
                                               values['familyID'])

        if fields:
            output = ' '.join(str(values[field]) for field in fields
                              if field in values)
            click.echo(output)
        else:
            if condense:
                dump = jsonify(values)
            else:
                raw_dump = yaml.safe_dump(values, default_flow_style=False,
                                          allow_unicode=True)
                dump = fix_dump(raw_dump)
                click.echo(click.style('>>> Sample: ', fg='red'), nl=False)
                click.echo(click.style(sample.id, bold=True, fg='red'))
                if sample.udf.get('cancelled') == 'yes':
                    click.echo(click.style('CANCELLED', bold=True, fg='yellow'))
            click.echo(dump)


@click.command()
@click.argument('lims_id')
@click.argument('field_key')
@click.argument('new_value')
@click.pass_context
def update(context, lims_id, field_key, new_value):
    """Update a UDF for a sample."""
    lims = api.connect(context.obj)
    lims_sample = lims.sample(lims_id)
    old_value = lims_sample.udf.get(field_key, 'N/A').encode('utf-8')
    click.echo("about to update sample: {}".format(lims_sample.id))
    message_tmlt = "are you sure you want to change '{}': '{}' -> '{}'"
    if click.confirm(message_tmlt.format(field_key, old_value, new_value)):
        lims_sample.udf[field_key] = new_value
        lims_sample.put()
