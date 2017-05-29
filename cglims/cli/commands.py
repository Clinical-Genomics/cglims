# -*- coding: utf-8 -*-
import logging

import click
import ruamel.yaml

from cglims import api
from cglims.api import Sample
from cglims.panels import convert_panels

log = logging.getLogger(__name__)


@click.command()
@click.option('-p', '--project', is_flag=True, help='identifier is a project')
@click.option('-n', '--external', is_flag=True, help='identifier is the customer sample name')
@click.option('-m', '--minimal', is_flag=True, help='output minimal information')
@click.option('--all', '--all-samples', is_flag=True, help='include cancelled/tumor samples')
@click.argument('identifier')
@click.argument('field', required=False)
@click.pass_context
def get(context, project, external, minimal, identifier, field, all_samples):
    """Get information from LIMS: either sample or family samples."""
    lims_api = api.connect(context.obj)
    if project:
        lims_samples = lims_api.get_samples(projectlimsid=identifier)
    elif identifier.startswith('cust'):
        # look up samples in a case
        lims_samples = lims_api.case(*identifier.split('-', 1))
    elif external:
        lims_samples = lims_api.get_samples(name=identifier)
    else:
        # look up a single sample
        is_cgid = True if identifier[0].isdigit() else False
        lims_samples = [lims_api.sample(identifier, is_cgid=is_cgid)]

    for lims_sample in lims_samples:
        sample_obj = Sample(lims_sample)
        if not all_samples and not sample_obj.to_analysis:
            log.debug("sample not for analysis: %s", sample_obj['id'])
            continue

        if field:
            if field not in sample_obj:
                log.error("can't find UDF on sample: %s", field)
                context.abort()
            elif isinstance(sample_obj[field], list):
                for item in sample_obj[field]:
                    click.echo(item)
            else:
                click.echo(sample_obj[field])
        else:
            dump = ruamel.yaml.round_trip_dump(dict(sample_obj))
            click.echo(click.style('>>> Sample: ', fg='red'), nl=False)
            click.echo(click.style(sample_obj['id'], bold=True, fg='red'))
            if sample_obj.get('cancelled') == 'yes':
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


@click.command()
@click.argument('customer')
@click.argument('default_panels', nargs=-1)
@click.pass_context
def panels(context, customer, default_panels):
    """Convert between default panels and gene list panels."""
    for panel_id in convert_panels(customer, default_panels):
        click.echo(panel_id)
