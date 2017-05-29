# -*- coding: utf-8 -*-
from datetime import datetime
import copy
import logging

import click
from dateutil.parser import parse as parse_date
import yaml

from cglims import api
from cglims.constants import SEX_MAP

log = logging.getLogger(__name__)


class ExportSamples(object):

    """Export information about a group of samples."""

    def __init__(self, lims_api):
        super(ExportSamples, self).__init__()
        self.lims = lims_api

    def __call__(self, customer_id, family_name):
        """Export information for a family of samples."""
        samples = self._fetch(customer_id, family_name)
        families_data = []
        samples_data = []
        for sample_obj in samples:
            family_data = self._get_familydata(sample_obj)
            families_data.append(family_data)

            lims_artifacts = self.lims.get_artifacts(samplelimsid=sample_obj['id'])
            artifact_data = self._parse_artifacts(lims_artifacts)
            sample_data = self._transform_sample(sample_obj)
            sample_data.update(artifact_data)
            samples_data.append(sample_data)

        export_data = self._consolidate_family(families_data)
        export_data['samples'] = samples_data
        return export_data

    def _fetch(self, customer_id, family_name):
        """Fetch all information from LIMS."""
        lims_samples = self.lims.case(customer_id, family_name)
        for lims_sample in lims_samples:
            sample_obj = api.Sample(lims_sample)
            yield sample_obj

    @staticmethod
    def _transform_sample(sample_obj):
        """Process a single sample with parsed artifact data."""
        capture_kit = sample_obj.get('Capture Library version')
        try:
            sample_data = {
                'id': sample_obj['id'],
                'name': sample_obj['name'],
                'status': sample_obj['Status'],
                'delivery': sample_obj['Data Analysis'],
                'sex': SEX_MAP.get(sample_obj.get('Gender'), 'N/A'),
                'app_tag': sample_obj['Sequencing Analysis'],
                'app_tag_version': int(sample_obj.get('Application Tag Version', '1')),
                'priority': sample_obj.get('priority', 'standard'),
                'capture_kit': capture_kit if capture_kit != 'NA' else None,
                'project': sample_obj.project['name'],
                'source': sample_obj.get('Source', 'N/A'),
            }
        except KeyError as error:
            log.error("missing UDF key for sample: %s", sample_obj['id'])
            click.echo(sample_obj.items(), err=True)
            raise error
        return sample_data

    @staticmethod
    def _get_familydata(sample_obj):
        """Parse out common (family-level) data."""
        family_data = {
            'customer': sample_obj['customer'],
            'family_id': sample_obj['familyID'],
            'case_id': sample_obj['case_id'],
            'gene_panels': sample_obj['panels'],
            'reference_genome': sample_obj.get('Reference Genome', 'hg19'),
        }
        return family_data

    @staticmethod
    def _consolidate_family(families_data):
        """Consolidate family data across multiple samples."""
        for index, family in enumerate(families_data):
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

    def _parse_artifacts(self, lims_artifacts):
        """Parse info from sample artifacts."""
        data = {}
        for artifact in lims_artifacts:
            if artifact.parent_process is None:
                continue
            elif artifact.parent_process.type.name == 'CG002 - Reception Control':
                udf_key = 'date arrived at clinical genomics'
                if artifact.parent_process.udf.get(udf_key):
                    data['received_at'] = artifact.parent_process.udf.get(udf_key)
            elif artifact.parent_process.type.id == '33':
                process = artifact.parent_process
                data['capture_kit'] = process.udf['Capture Library version']
                data['library_prep_method'] = process.udf['Method document and version no:']
                data['library_prep_lotno'] = process.udf['Lot no: Capture library']
            elif artifact.parent_process.type.id == '667':
                # PCR Free library prep
                method_no = artifact.parent_process.udf['Method document']
                method_version = artifact.parent_process.udf['Method document version']
                data['library_prep_method'] = ":".join([method_no, method_version])
            elif artifact.parent_process.type.id == '663':
                # sequencing (cluster generation...)
                method_no = artifact.parent_process.udf['Method']
                method_version = artifact.parent_process.udf['Version']
                data['sequencing_method'] = ":".join([method_no, method_version])
                data['flowcell'] = artifact.parent_process.udf['Experiment Name']
            elif artifact.parent_process.type.id in ('670', '671'):
                # more seq (actual sequencing process)
                # or for EX: CG002 - Illumina Sequencing (Illumina SBS)
                if 'sequencing_date' not in data:
                    # get the start date for sequenceing
                    data['sequencing_date'] = parse_date(artifact.parent_process.date_run)
            elif artifact.parent_process.type.id == '159':
                # delivery
                delivery_date = artifact.parent_process.udf['Date delivered']
                data['delivery_date'] = datetime.combine(delivery_date, datetime.min.time())
                method_no = artifact.parent_process.udf['Method Document']
                method_version = artifact.parent_process.udf['Method Version']
                data['delivery_method'] = ':'.join([method_no, method_version])
            elif artifact.parent_process.type.id == '669':
                # CG002 - Hybridize Library  (SS XT)
                process = artifact.parent_process
                capture_kit_udf = 'SureSelect capture library/libraries used'
                data['capture_kit'] = process.udf[capture_kit_udf]
                method_no = process.udf['Method document']
                method_version = artifact.parent_process.udf['Method document versio']
                data['library_prep_method'] = ':'.join([method_no, method_version])
            elif artifact.parent_process.type.id == '664':
                # CG002 - Cluster Generation (Illumina SBS)
                method_no = artifact.parent_process.udf['Method Document 1']
                method_version = artifact.parent_process.udf['Document 1 Version']
                data['sequencing_method'] = ':'.join([method_no, method_version])
                raw_flowcell = artifact.parent_process.udf['Experiment Name']
                data['flowcell'] = raw_flowcell.split(' ')[0]
        return data


@click.command()
@click.argument('customer_or_case')
@click.argument('family_name', required=False)
@click.pass_context
def export(context, customer_or_case, family_name):
    """Parse out interesting data about a case."""
    lims_api = api.connect(context.obj)
    case_exporter = ExportSamples(lims_api)

    if family_name:
        customer_id = customer_or_case
    else:
        customer_id, family_name = customer_or_case.split('-', 1)

    export_data = case_exporter(customer_id, family_name)
    raw_dump = yaml.safe_dump(export_data, default_flow_style=False, allow_unicode=True)
    click.echo(raw_dump)
