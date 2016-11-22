# -*- coding: utf-8 -*-
from datetime import datetime
from copy import deepcopy

import click

from cglims.pedigree import make_pedigree
from cglims import api
from .utils import jsonify

SEX_MAP = {'F': 'female', 'M': 'male', 'Unknown': 'unknown'}


@click.command()
@click.option('-g', '--gene-panel', help='custom gene panel')
@click.option('-s', '--samples', multiple=True, help='included samples')
@click.argument('customer')
@click.argument('family', required=False)
@click.pass_context
def pedigree(context, gene_panel, samples, customer, family):
    """Create pedigree from LIMS."""
    lims = api.connect(context.obj)
    if customer and family:
        lims_samples = lims.case(customer, family)
        family_id = None
    elif samples:
        lims_samples = [lims.sample(sample_id) for sample_id in samples]
        family_id = customer
    else:
        click.echo("you need to provide customer+family or samples")
        context.abort()
    content = make_pedigree(lims, lims_samples, family_id=family_id,
                            gene_panel=gene_panel)
    click.echo(content)


@click.command()
@click.option('-p', '--pretty', is_flag=True, help='pretty print JSON')
@click.argument('identifier')
@click.argument('fields', nargs=-1, required=False)
@click.pass_context
def get(context, pretty, identifier, fields):
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
            click.echo(jsonify(values, pretty=pretty))


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
