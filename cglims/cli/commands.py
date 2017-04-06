# -*- coding: utf-8 -*-
import logging

import click
import yaml

from cglims import api
from cglims.api import ClinicalSample
from cglims.apptag import UnknownSequencingTypeError
from cglims.config import make_config, CAPTUREKIT_MAP, relevant_samples
from cglims.pedigree import make_pedigree
from cglims.panels import convert_panels
from .utils import jsonify, fix_dump

CAPTUREKITS = CAPTUREKIT_MAP.values()
log = logging.getLogger(__name__)


@click.command()
@click.option('-g', '--gene-panel', help='custom gene panel')
@click.option('-f', '--family-id', help='custom family id')
@click.option('-s', '--samples', multiple=True, help='included samples')
@click.argument('customer_family', nargs=2, required=False)
@click.pass_context
def pedigree(context, gene_panel, family_id, samples, customer_family):
    """DEPRECATED: Create pedigree from LIMS."""
    lims_api = api.connect(context.obj)
    if customer_family:
        lims_samples = lims_api.case(*customer_family)
    elif samples:
        lims_samples = [lims_api.sample(sample_id) for sample_id in samples]
    else:
        click.echo("you need to provide customer+family or samples")
        context.abort()
    content = make_pedigree(lims_api, lims_samples, family_id=family_id,
                            gene_panel=gene_panel)
    click.echo(content)


@click.command()
@click.option('-g', '--gene-panel', help='custom gene panel')
@click.option('-f', '--family-id', help='custom family id')
@click.option('-s', '--samples', multiple=True, help='included samples')
@click.option('-c', '--capture-kit', type=click.Choice(CAPTUREKITS),
              help='custom capture kit')
@click.option('--force', is_flag=True, help='skip sanity checks')
@click.argument('raw_case_id')
@click.pass_context
def config(context, gene_panel, family_id, samples, capture_kit, force,
           raw_case_id):
    """Create pedigree YAML file from LIMS data."""
    if '--' in raw_case_id:
        case_id, ext = raw_case_id.split('--', 1)
    else:
        case_id, ext = raw_case_id, None
    customer, family = case_id.split('-', 1)

    lims_api = api.connect(context.obj)
    gene_panels = [gene_panel] if gene_panel else None

    if samples:
        lims_samples = [lims_api.sample(sample_id) for sample_id in samples]
    else:
        lims_samples = lims_api.case(customer, family)

    included_samples = relevant_samples(lims_samples)
    data = make_config(lims_api, included_samples, family_id=family_id,
                       gene_panels=gene_panels, capture_kit=capture_kit, force=force)

    if ext:
        # handle cases with e.g. downsampled data
        data['family'] = '--'.join([data['family'], ext])
        for sample in data['samples']:
            sample['sample_id'] = '--'.join([sample['sample_id'], ext])

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
@click.option('-n', '--external', is_flag=True, help='identifier is the customer sample name')
@click.option('-m', '--minimal', is_flag=True, help='output minimal information')
@click.option('--all', '--all-samples', is_flag=True,
              help='include cancelled/tumor samples')
@click.argument('raw_identifier')
@click.argument('field', required=False)
@click.pass_context
def get(context, condense, project, external, minimal, raw_identifier, field, all_samples):
    """Get information from LIMS: either sample or family samples."""
    if '--' in raw_identifier:
        identifier, ext = raw_identifier.split('--', 1)
    else:
        identifier, ext = raw_identifier, None

    lims = api.connect(context.obj)
    if project:
        lims_samples = lims.get_samples(projectlimsid=identifier)
    elif identifier.startswith('cust'):
        # look up samples in a case
        lims_samples = lims.case(*identifier.split('-', 1))
    elif external:
        lims_samples = lims.get_samples(name=identifier)
    else:
        # look up a single sample
        is_cgid = True if identifier[0].isdigit() else False
        lims_samples = [lims.sample(identifier, is_cgid=is_cgid)]

    if len(lims_samples) > 1 and not all_samples:
        # filter out tumor and cancelled samples
        lims_samples = relevant_samples(lims_samples)

    for lims_sample in lims_samples:
        sample_obj = ClinicalSample(lims_sample)
        data = sample_obj.to_dict(minimal=minimal)
        data['sample_id'] = "{}--{}".format(data['sample_id'], ext) if ext else data['sample_id']
        data['case_id'] = "{}--{}".format(data['case_id'], ext) if ext else data['case_id']

        if field:
            if field not in data:
                log.error("can't find UDF on sample: %s", field)
                context.abort()
            elif isinstance(data[field], list):
                for item in data[field]:
                    click.echo(item)
            else:
                click.echo(data[field])
        else:
            if condense:
                dump = jsonify(data)
            else:
                raw_dump = yaml.safe_dump(data, default_flow_style=False,
                                          allow_unicode=True)
                dump = fix_dump(raw_dump)
                click.echo(click.style('>>> Sample: ', fg='red'), nl=False)
                click.echo(click.style(data['id'], bold=True, fg='red'))
                if data.get('cancelled') == 'yes':
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
    gender = lims_sample.udf.get('Gender')
    if gender:
        lims_sample.udf['Gender'] = gender.upper()
    else:
        lims_sample.udf['Gender'] = 'unknown'
    if lims_sample.udf.get('Status'):
        lims_sample.udf['Status'] = lims_sample.udf.get('Status').lower()

    if lims_sample.udf.get('Source') == 'Blod':
        log.info("updating 'Source': 'Blod' => 'blood'")
        lims_sample.udf['Source'] = 'blood'

    if 'priority' in lims_sample.udf:
        if lims_sample.udf.get('priority') == 'prioriterad':
            log.info("updating 'priority': 'prioriterad' => 'priority'")
            lims_sample.udf['priority'] = 'priority'
        else:
            lims_sample.udf['priority'] = lims_sample.udf['priority'].lower()
    else:
        log.info("missing 'priority' => setting to 'standard'")
        lims_sample.udf['priority'] = 'standard'

    process_only = lims_sample.udf.get('Process only if QC OK')
    if process_only == 'Ja':
        log.info("translating 'QC OK' field: 'Ja' => 'yes'")
        lims_sample.udf['Process only if QC OK'] = 'yes'
    elif process_only == 'Nej':
        log.info("translating 'QC OK' field: 'Nej' => 'no'")
        lims_sample.udf['Process only if QC OK'] = 'no'
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


@click.command()
@click.option('-d', '--delivered', is_flag=True, help='check if sample is delivered')
@click.argument('lims_id')
@click.pass_context
def sample(context, delivered, lims_id):
    """Fetch information about a sample."""
    lims_api = api.connect(context.obj)
    if delivered:
        delivery_date = lims_api.is_delivered(lims_id)
        if delivery_date:
            click.echo(delivery_date)
        else:
            log.error("sample not yet delivered")
            context.abort()
