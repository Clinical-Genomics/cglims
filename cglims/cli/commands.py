# -*- coding: utf-8 -*-
from datetime import datetime
from copy import deepcopy

import click

from cglims.pedigree import make_pedigree
from .utils import connect_api, jsonify


@click.command()
@click.argument('customer')
@click.argument('family')
@click.pass_context
def pedigree(context, customer, family):
    """Create pedigree from LIMS."""
    api = connect_api(context.obj)
    content = make_pedigree(api, customer, family)
    click.echo(content, nl=False)


@click.command()
@click.option('-p', '--pretty', is_flag=True, help='pretty print JSON')
@click.option('-f', '--fields', nargs=-1, help='print specific fields only')
@click.argument('identifier')
@click.pass_context
def get(context, pretty, fields, identifier):
    """Get information from LIMS: either sample or family samples."""
    api = connect_api(context.obj)
    if identifier.startswith('cust'):
        # look up samples in a case
        samples = api.case(*identifier.split('-', 1))
    else:
        # look up a single sample
        is_cgid = True if identifier[0].isdigit() else False
        samples = [api.sample(identifier, is_cgid=is_cgid)]

    for sample in samples:
        values = deepcopy(sample.udf._lookup)
        values['id'] = sample.id
        values['name'] = sample.name
        date_parts = map(int, sample.date_received.split('-'))
        values['date_received'] = datetime(*date_parts)
        values['project_name'] = sample.project.name

        if fields:
            output = ' '.join(values[field] for field in fields
                              if field in values)
            click.echo(output, nl=False)
        else:
            click.echo(jsonify(fields, pretty=pretty))


@click.command()
@click.argument('lims_id')
@click.argument('field_key')
@click.argument('new_value')
@click.pass_context
def update(context, lims_id, field_key, new_value):
    """Update a UDF for a sample."""
    api = connect_api(context.obj)
    lims_sample = api.sample(lims_id)
    old_value = lims_sample.udf.get(field_key, 'N/A')
    click.echo("about to update sample: {}".format(lims_sample.id))
    message_tmlt = "are you sure you want to change '{}': '{}' -> '{}'"
    if click.confirm(message_tmlt.format(field_key, old_value, new_value)):
        lims_sample.udf[field_key] = new_value
        lims_sample.put()
