# -*- coding: utf-8 -*-
import logging

import click
from genologics.entities import Process

from cglims import api
from cglims.apptag import ApplicationTag

RELATION_UDS = ['motherID', 'fatherID', 'Other relations']
log = logging.getLogger(__name__)


@click.command()
@click.option('-s', '--source',
              type=click.Choice(['project', 'process']), default='project')
@click.argument('lims_id')
@click.pass_context
def samples(context, source, apptags, lims_id):
    """Fetch projects from the database."""
    lims = api.connect(context.obj)
    if source == 'process':
        lims_process = Process(lims, id=lims_id)
        lims_samples = process_samples(lims_process)
    elif source == 'project':
        lims_samples = ({'sample': sample} for sample in
                        lims.get_samples(projectlimsid=lims_id))
    for lims_sample in lims_samples:
        click.echo(lims_sample.id)


@click.command()
@click.option('-u', '--update', is_flag=True, help='update sample UDFs')
@click.option('-f', '--force', is_flag=True, help='update existing values')
@click.option('-v', '--version', type=int, help='application tag version')
@click.option('-s', '--source',
              type=click.Choice(['sample', 'project', 'process']),
              default='sample')
@click.argument('lims_id')
@click.pass_context
def check(context, update, version, force, source, lims_id):
    """Check LIMS sample or all samples in a process."""
    lims = api.connect(context.obj)
    if source == 'sample':
        lims_samples = [{'sample': lims.sample(lims_id)}]
    elif source == 'process':
        lims_process = Process(lims, id=lims_id)
        lims_samples = process_samples(lims_process)
    elif source == 'project':
        lims_samples = ({'sample': sample} for sample in
                        lims.get_samples(projectlimsid=lims_id))

    for sample in lims_samples:
        check_sample(lims, sample['sample'], lims_artifact=sample.get('artifact'),
                     update=update, version=version, force=force)


def check_sample(lims, lims_sample, lims_artifact=None, update=False, version=None,
                 force=False):
    """Check a LIMS sample and optionally update some UDFs."""
    results = []
    log.info("checking sample: %s (%s)", lims_sample.id, lims_sample.name)
    log.debug('checking sample name...')
    results.append(check_samplename(lims_sample))
    log.debug('checking duplicate external sample name...')
    results.append(check_duplicatename(lims, lims_sample))
    log.debug('checking capture kit (extenal sequencing)...')
    results.append(check_capturekit(lims_sample))
    log.debug('checking family members...')
    results.append(check_familymembers(lims, lims_sample))

    if update:
        log.debug('updating missing reads...')
        set_missingreads(lims_sample, force=force)
        log.debug('checking if update to trio tag is possible...')
        set_trioapptag(lims, lims_sample)
        if version:
            log.debug('updating application tag version...')
            set_apptagversion(lims_sample, version, force=force)

        if lims_artifact:
            if lims_artifact.qc_flag:
                log.warn("qc flag already set: %s", lims_artifact.qc_flag)

            if False in results:
                log.warn("sample check FAILED: %s", lims_sample.id)
                lims_artifact.qc_flag = 'FAILED'
            else:
                log.info("sample check PASSED: %s", lims_sample.id)
                lims_artifact.qc_flag = 'PASSED'
            lims_artifact.put()


def set_missingreads(lims_sample, force=False):
    """Set the 'Reads Missing (M)' UDF base on app tag."""
    raw_apptag = lims_sample.udf['Sequencing Analysis']
    app_tag = ApplicationTag(raw_apptag)
    target_amount = app_tag.reads
    missing_reads = lims_sample.udf.get('Reads missing (M)')
    if not force and missing_reads is not None:
        log.warn("missing reads already set: %s", missing_reads)
    else:
        lims_sample.udf['Reads missing (M)'] = target_amount
        log.info("updating reads missing")
        lims_sample.put()


def set_apptagversion(lims_sample, version, force=False):
    """Set the Application Tag Version for a sample."""
    current_version = lims_sample.udf.get('Application Tag Version')
    if not force and current_version:
        log.warn("application tag version already set: %s", current_version)
    else:
        lims_sample.udf['Application Tag Version'] = version
        log.info("updating application tag version: %s", version)
        lims_sample.put()


def set_trioapptag(lims, lims_sample):
    """Update the application tag if a WGS trio has been sent in."""
    related_samples = lims.case(lims_sample.udf['customer'],
                                lims_sample.udf['familyID'])
    if len(related_samples) == 3:
        log.debug("found three related samples")
        # Q: should more than 3 samples be allowed?
        app_tags = set(sample.udf['Sequencing Analysis'] for sample in
                       related_samples)
        allowed_tags = set(['WGSPCFC030', 'WGTPCFC030'])
        if len(app_tags.difference(allowed_tags)) == 0:
            # then we can update the application tag for the sample
            log.info("found 3 related samples with WGS application tag")
            log.info("updating to trio WGS tag: %s", lims_sample.id)
            lims_sample.udf['Sequencing Analysis'] == 'WGTPCFC030'
            lims_sample.put()


def check_samplename(lims_sample):
    """Check external sample name conventions.

    Sample name are allowed to contain alphanumeric characters
    AND '-' (dash). Nothing else.
    """
    no_dash = lims_sample.name.replace('-', '')
    if not no_dash.isalnum():
        log.error("sample name not OK: %s", lims_sample.name)
        return False
    else:
        return True


def check_duplicatename(lims, lims_sample):
    """Check if the same customer has sent in a sample with the same id."""
    result = True
    samples = lims.get_samples(name=lims_sample.name,
                               udf={'customer': lims_sample.udf['customer']})
    for other_sample in samples:
        if other_sample.id != lims_sample.id:
            # same sample id twice!
            if other_sample.udf.get('cancelled') == 'yes':
                log.info("duplicate sample but the other is cancelled")
            else:
                log.error("sample name duplicate: %s | %s", lims_sample.id,
                          other_sample.id)
                result = False
    return result


def check_capturekit(lims_sample):
    """Check if no capture kit doesn't exist for external samples."""
    app_tag = lims_sample.udf['Sequencing Analysis']
    if app_tag.startswith('EXX'):
        # now we need a capture kit to be filled in
        capture_kit = lims_sample.udf['Capture Library version']
        if capture_kit == 'NA':
            log.error("capture kit not filled in for external sample")
            return False
    return True


def check_familymembers(lims, lims_sample):
    """Check if sample has family memeber but no relations to them."""
    result = True
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
                            result = False
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
                result = False
    return result


def process_samples(lims_process):
    """Retrieve LIMS input samples from a process."""
    for artifact in lims_process.all_inputs():
        for lims_sample in artifact.samples:
            yield {'sample': lims_sample, 'artifact': artifact}
