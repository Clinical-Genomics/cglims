# -*- coding: utf-8 -*-
from datetime import datetime
from copy import deepcopy
import logging

import click
import yaml

from cglims import api
from cglims.api import ClinicalSample
from cglims.config import make_config
from cglims.pedigree import make_pedigree
from cglims.constants import SEX_MAP
from cglims.panels import convert_panels
from .utils import jsonify, fix_dump, ordered_reads, relevant_samples

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
@click.option('-c', '--capture-kit', help='custom capture kit')
@click.argument('customer_or_case')
@click.argument('family', required=False)
@click.pass_context
def config(context, gene_panel, family_id, samples, capture_kit, customer_or_case,
           family):
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

    included_samples = relevant_samples(lims_samples)
    data = make_config(lims_api, included_samples, family_id=family_id,
                       gene_panels=gene_panels, capture_kit=capture_kit)
    # handle single sample cases with 'unknown' phenotype
    if len(data['samples']) == 1:
        if data['samples'][0]['phenotype'] == 'unknown':
            log.info("setting 'unknown' phenotype to 'unaffected'")
            data['samples'][0]['phenotype'] = 'unaffected'
    dump = yaml.safe_dump(data, default_flow_style=False, allow_unicode=True)
    click.echo(fix_dump(dump))


@click.command()
@click.option('-c', '--condense', is_flag=True, help='condense output')
@click.option('-p', '--project', is_flag=True, help='identifier is a project')
@click.option('--all', '--all-samples', is_flag=True,
              help='include cancelled/tumor samples')
@click.argument('identifier')
@click.argument('field', required=False)
@click.pass_context
def get(context, condense, project, identifier, field, all_samples):
    """Get information from LIMS: either sample or family samples."""
    lims = api.connect(context.obj)
    if project:
        lims_samples = api.get_samples(projectname=identifier)
    elif identifier.startswith('cust'):
        # look up samples in a case
        lims_samples = lims.case(*identifier.split('-', 1))
    else:
        # look up a single sample
        is_cgid = True if identifier[0].isdigit() else False
        lims_samples = [lims.sample(identifier, is_cgid=is_cgid)]

    if len(lims_samples) > 1 and not all_samples:
        # filter out tumor and cancelled samples
        lims_samples = relevant_samples(lims_samples)

    for sample in lims_samples:
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

        clinical_sample = ClinicalSample(sample) # upgrade!
        values['is_human'] = clinical_sample.apptag.is_human
        values['is_production'] = (False if values['customer'] == 'cust000'
                                   else True)
        values['pipeline'] = clinical_sample.pipeline

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
    lims_sample.udf['Concentration (nM)'] = 'NA'
    lims_sample.udf['Volume (uL)'] = 'NA'
    lims_sample.udf['Capture Library version'] = 'NA'
    lims_sample.udf['Strain'] = 'NA'
    lims_sample.udf['Source'] = 'other'
    lims_sample.udf['Index type'] = 'NA'
    lims_sample.udf['Index number'] = 'NA'
    lims_sample.udf['Sample Buffer'] = 'NA'
    lims_sample.udf['Reference Genome Microbial'] = 'NA'

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
