# -*- coding: utf-8 -*-
import logging

import click

from cglims import api
from cglims.apptag import ApplicationTag

RELATION_UDS = ['motherID', 'fatherID', 'Other relations']
log = logging.getLogger(__name__)


@click.command()
@click.option('-p', '--project', help='LIMS project id')
@click.option('-l', '--limit', default=20, help='number of samples to fetch')
@click.pass_context
def samples(context, project, limit):
    """Fetch projects from the database."""
    lims = api.connect(context.obj)
    samples = lims.get_samples(projectlimsid=project)
    if project is None:
        samples = samples[:limit]
    for sample in samples:
        click.echo(sample.id)


@click.command()
@click.option('-u', '--update', is_flag=True, help='update sample UDFs')
@click.option('-f', '--force', is_flag=True, help='update existing values')
@click.option('-v', '--version', type=int, help='application tag version')
@click.argument('lims_id')
@click.pass_context
def check(context, update, version, force, lims_id):
    """Check samples in a project."""
    lims = api.connect(context.obj)
    # get sample in the project
    lims_sample = lims.sample(lims_id)
    check_samplename(lims_sample)
    check_duplicatename(lims, lims_sample)
    check_capturekit(lims_sample)
    check_familymembers(lims, lims_sample)

    if update:
        set_missingreads(lims_sample, force=force)
        set_trioapptag(lims, lims_sample)
        if version:
            set_apptagversion(lims_sample, version, force=force)


def set_missingreads(lims_sample, force=False):
    """Set the 'Reads Missing (M)' UDF base on app tag."""
    raw_apptag = lims_sample.udf['Sequencing Analysis']
    app_tag = ApplicationTag(raw_apptag)
    target_amount = app_tag.reads
    missing_reads = lims_sample.udf.get('Reads missing (M)')
    if not force and missing_reads:
        log.warn("missing reads already set: %s", missing_reads)
    else:
        lims_sample.udf['Reads missing (M)'] = target_amount
        log.info("updating reads missing")
        lims_sample.put()


def set_apptagversion(lims_sample, version, force=False):
    """Set the Application Tag Version for a sample."""
    current_version = lims_sample.udf.get('Application Tag Version')
    if not force and current_version:
        lims_sample.udf['Application Tag Version'] = version
        log.info("updating application tag version")
        lims_sample.put()
    else:
        log.warn("application tag version already set: %s", current_version)


def set_trioapptag(lims, lims_sample):
    """Update the application tag if a WGS trio has been sent in."""
    related_samples = lims.case(lims_sample.udf['customer'],
                                lims_sample.udf['familyID'])
    if len(related_samples) == 3:
        log.debug("found three related samples")
        # Q: should more than 3 samples be allowed?
        app_tags = set(sample.udf['Sequencing Analsysis'] for sample in
                       related_samples)
        allowed_tags = set(['WGSPCFC030', 'WGTPCFC030'])
        if len(app_tags.difference(allowed_tags)) == 0:
            # then we can update the application tag for the sample
            log.info("found 3 related samples with WGS application tag")
            log.info("updating to trio WGS tag: %s", lims_sample.id)
            lims_sample.udf['Sequencing Analsysis'] == 'WGTPCFC030'
            lims_sample.put()


def check_samplename(lims_sample):
    """Check external sample name conventions.

    Sample name are allowed to contain alphanumeric characters
    AND '-' (dash). Nothing else.
    """
    no_dash = lims_sample.name.replace('-', '')
    if not no_dash.isalnum():
        log.error("sample name not OK: %s", lims_sample.name)


def check_duplicatename(lims, lims_sample):
    """Check if the same customer has sent in a sample with the same id."""
    samples = lims.get_samples(name=lims_sample.name,
                               udf={'customer': lims_sample.udf['customer']})
    for other_sample in samples:
        if other_sample.id != lims_sample.id:
            # same sample id twice!
            if other_sample.udf.get('cancelled') == 'yes':
                log.debug("duplicate sample but the other is cancelled")
            else:
                log.error("sample name duplicate: %s | %s", lims_sample.id,
                          other_sample.id)


def check_capturekit(lims_sample):
    """Check if no capture kit doesn't exist for external samples."""
    app_tag = lims_sample.udf['Sequencing Analysis']
    if app_tag.startswith('EXX'):
        # now we need a capture kit to be filled in
        capture_kit = lims_sample.udf['Capture Library version']
        if capture_kit == 'NA':
            log.error("capture kit not filled in for external sample")


def check_familymembers(lims, lims_sample):
    """Check if sample has family memeber but no relations to them."""
    related_samples = lims.case(lims_sample.udf['customer'],
                                lims_sample.udf['familyID'])
    if len(related_samples) > 1:
        # sample is part of a family/case
        samples = {}
        is_family = False
        for sample in related_samples:
            if any(sample.udf.get(udf_key) for udf_key in RELATION_UDS):
                is_family = True
            samples[sample.name] = sample

        if is_family:
            for sample in related_samples:
                for udf_key in RELATION_UDS:
                    related_id = sample.udf.get(udf_key)
                    if related_id:
                        if related_id not in samples:
                            log.error("related sample not part of family")
                            log.error("original sample, %s", lims_sample.id)
                            log.error("family: %s", lims_sample.udf['familyID'])
                            log.error("other sample (missing): %s", related_id)
                        else:
                            log.debug("found related sample: %s = %s", udf_key,
                                      samples[related_id].id)
        else:
            # perhaps a tumor/normal pair?
            tumor_samples = (sample.udf.get('tumor') == 'yes' for sample in
                             related_samples)
            if any(tumor_samples):
                log.debug("samples part of cancer combo")
            else:
                log.error("samples in 'family' not related, tumor/normal?")
