# -*- coding: utf-8 -*-
from datetime import datetime
from copy import deepcopy
import logging

import click
import yaml

from cglims import api
from cglims.apptag import ApplicationTag
from cglims.config import make_config
from cglims.pedigree import make_pedigree
from cglims.constants import SEX_MAP
from cglims.panels import convert_panels
from .utils import jsonify, fix_dump, ordered_reads

log = logging.getLogger(__name__)


@click.command()
@click.option('-g', '--gene-panel', help='custom gene panel')
@click.option('-f', '--family-id', help='custom family id')
@click.option('-s', '--samples', multiple=True, help='included samples')
@click.argument('customer_family', nargs=2, required=False)
@click.pass_context
def pedigree(context, gene_panel, family_id, samples, customer_family):
    """Create pedigree from LIMS."""
    lims = api.connect(context.obj)
    if customer_family:
        lims_samples = lims.case(*customer_family)
    elif samples:
        lims_samples = [lims.sample(sample_id) for sample_id in samples]
    else:
        click.echo("you need to provide customer+family or samples")
        context.abort()
    content = make_pedigree(lims, lims_samples, family_id=family_id,
                            gene_panel=gene_panel)
    click.echo(content)


@click.command()
@click.option('-g', '--gene-panel', help='custom gene panel')
@click.option('-f', '--family-id', help='custom family id')
@click.option('-s', '--samples', multiple=True, help='included samples')
@click.argument('customer_or_case')
@click.argument('family', required=False)
@click.pass_context
def config(context, gene_panel, family_id, samples, customer_or_case, family):
    """Create pedigree from LIMS."""
    lims_api = api.connect(context.obj)
    gene_panels = [gene_panel] if gene_panel else None
    if customer_or_case:
        if family is None:
            customer, family = customer_or_case.split('-', 1)
        else:
            customer = customer_or_case
        lims_samples = lims_api.case(customer, family)
    elif samples:
        lims_samples = [lims_api.sample(sample_id) for sample_id in samples]
    data = make_config(lims_api, lims_samples, family_id=family_id,
                       gene_panels=gene_panels)
    dump = yaml.safe_dump(data, default_flow_style=False, allow_unicode=True)
    click.echo(fix_dump(dump))


@click.command()
@click.option('-c', '--condense', is_flag=True, help='condense output')
@click.option('-p', '--project', is_flag=True, help='identifier is a project')
@click.argument('identifier')
@click.argument('field', required=False)
@click.pass_context
def get(context, condense, project, identifier, field):
    """Get information from LIMS: either sample or family samples."""
    lims = api.connect(context.obj)
    if project:
        samples = api.get_samples(projectname=identifier)
    elif identifier.startswith('cust'):
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
        values['reads'] = ordered_reads(values['Sequencing Analysis'])
        values['expected_reads'] = int(values['reads'] * .75)
        values['project_id'] = sample.project.id

        apptag = ApplicationTag(values['Sequencing Analysis'])
        values['is_human'] = apptag.is_human
        values['is_production'] = (False if values['customer'] == 'cust000'
                                   else True)
        if values.get('tissue_type') != 'tumour':
            values['pipeline'] = 'mip' if values['is_human'] else 'mwgs'

        if 'customer' in values and 'familyID' in values:
            values['case_id'] = "{}-{}".format(values['customer'],
                                               values['familyID'])

        if 'customer' in values and 'Gene List' in values:
            default_panels = values['Gene List'].split(';')
            values['panels'] = default_panels

        if field:
            if field not in values:
                log.error("can't find UDF on sample: %s", field)
                context.abort()
            elif isinstance(values[field], list):
                for item in values[field]:
                    click.echo(item)
            else:
                click.echo(values[field])
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


@click.command()
@click.argument('sample_id')
@click.pass_context
def fillin(context, sample_id):
    """Fill in defaults for a LIMS sample."""
    lims_api = api.connect(context.obj)
    lims_sample = lims_api.sample(sample_id)
    click.echo("filling in defaults...")
    set_defaults(lims_sample)
    lims_sample.put()
    click.echo("saved new defaults")


def set_defaults(lims_sample):
    """Set default values for required UDFs."""
    log.info("setting defaults for required fields")
    lims_sample.udf['Concentration (nM)'] = 'na'
    lims_sample.udf['Volume (uL)'] = 'na'
    lims_sample.udf['Capture Library version'] = 'na'
    lims_sample.udf['Strain'] = 'na'
    lims_sample.udf['Source'] = 'other'
    lims_sample.udf['Index type'] = 'na'
    lims_sample.udf['Index number'] = 'na'
    lims_sample.udf['Sample Buffer'] = 'na'
    lims_sample.udf['Reference Genome Microbial'] = 'na'

    if 'priority' in lims_sample.udf:
        lims_sample.udf['priority'] = lims_sample.udf['priority'].lower()
    else:
        log.info("missing 'priority' => setting to 'standard'")
        lims_sample.udf['priority'] = 'standard'

    process_only = lims_sample.udf.get('Process only if QC OK')
    if process_only == 'Ja':
        log.info("translating 'QC OK' field: 'Ja' => 'yes'")
        lims_sample.udf['Process only if QC OK'] = 'yes'
    elif process_only is None:
        log.info("setting 'QC OK' field to default: 'NA'")
        lims_sample.udf['Process only if QC OK'] = 'NA'


@click.command()
@click.argument('customer')
@click.argument('default_panels', nargs=-1)
@click.pass_context
def panels(context, customer, default_panels):
    """Convert between default panels and gene list panels."""
    for panel_id in convert_panels(customer, default_panels):
        click.echo(panel_id)
