# -*- coding: utf-8 -*-
from copy import deepcopy
import re

from dateutil.parser import parse as parse_date
from genologics.entities import Sample
from genologics.lims import Lims

from cglims.apptag import ApplicationTag
from cglims.constants import READS_PER_1X, SEX_MAP
from cglims.exc import MultipleSamplesError

SAMPLE_REF = 'hg19'

def connect(config):
    """Connect and return API reference."""
    api = ClinicalLims(config['host'], config['username'], config['password'])
    return api


class ClinicalSample(object):

    def __init__(self, lims_sample):
        """ Wrapper around the genologics Sample class

        Args:
            lims_sample (genologics.Sample): the sample instance to extend
        """
        self.lims = lims_sample
        self._apptag = ApplicationTag(self.lims.udf['Sequencing Analysis'])

    @property
    def apptag(self):
        """ Init an instance of ApplicationTag based on the sample's apptag

        Returns: ApplicationTag.
        """
        return self._apptag

    @property
    def pipeline(self):
        """ Determines in which pipeline the sample needs to be run.

        Returns (str): 'mip' or 'mwgs'
        """
        if self.lims.udf.get('tissue_type') != 'tumour':
            if self.apptag.is_human:
                return 'mip'
        if self.apptag.is_microbial:
            return 'mwgs'

        return None

    @property
    def sex(self):
        """Return human readable form of sex (Gender)."""
        return SEX_MAP.get(self.udf('Gender'), None)

    @property
    def ordered_reads(self):
        """Calculate ordered number of reads."""
        app_tag = self.udf('Sequencing Analysis')
        type_id = app_tag[-4]
        number = int(app_tag[-3:])
        if type_id == 'R':
            return number * 1000000
        elif type_id == 'K':
            return number * 1000
        elif type_id == 'C':
            # expect WGS
            return number * READS_PER_1X
        else:
            raise ValueError("unknown read type id: {}".format(type_id))

    @property
    def expected_reads(self):
        """Calculate expected number of reads to sequence."""
        return int(self.ordered_reads * .75)

    def udf(self, udf_key, default=None):
        """Get a sample UDF."""
        return self.lims.udf.get(udf_key, default)

    @property
    def sample_id(self):
        """Get the official sample id."""
        return self.udf('Clinical Genomics ID') or self.lims.id

    def to_dict(self, minimal=False):
        """Export data from the sample object."""
        if self.udf('customer') and self.udf('familyID'):
            case_id = '-'.join([self.udf('customer'), self.udf('familyID')])
        else:
            case_id = 'NA'

        data = deepcopy(self.lims.udf._lookup)
        data.update(dict(
            id=self.lims.id,
            # general sample id if imported from old TSL
            sample_id=self.sample_id,
            name=self.lims.name,
            project_name=self.lims.project.name,
            project_id=self.lims.project.id,
            case_id=case_id,
        ))

        if not minimal:
            data.update(dict(
                date_received=parse_date(self.lims.date_received),
                sex=self.sex,
                reads=self.ordered_reads,
                expected_reads=self.expected_reads,
                is_human=self.apptag.is_human,
                sequencing_type=self.apptag.sequencing_type,
                is_external=self.apptag.is_external,
                pipeline=self.pipeline or 'NA',
                is_production=(False if data['customer'] == 'cust000' else True),
                panels=(self.udf('Gene List').split(';') if self.udf('Gene List') else None),
            ))
        return data


class SamplesheetHandler(object):

    def _get_placement_lane(self, lane):
        """Parse out the lane information from an artifact.placement"""
        return int(lane.split(':')[0])

    def _get_index(self, label):
        """Parse out the sequence from a reagent label"""

        reagent_types = self.get_reagent_types(name=label)

        if len(reagent_types) > 1:
            raise ValueError("Expecting at most one reagent type. Got ({}).".format(len(reagent_types)))

        try:
            reagent_type = reagent_types.pop()
        except IndexError:
            return ''
        sequence = reagent_type.sequence

        match = re.match(r"^.+ \((.+)\)$", label)
        if match:
            assert match.group(1) == sequence

        return sequence

    def _get_reagent_label(self, artifact):
        """Get the first and only reagent label from an artifact"""
        labels = artifact.reagent_labels
        if len(labels) > 1:
            raise ValueError("Expecting at most one reagent label. Got ({}).".format(len(labels)))
        return labels[0] if labels else None

    def _get_non_pooled_artifacts(self, artifact):
        """Find the parent artifact of the sample. Should hold the reagent_label"""
        artifacts = []

        if len(artifact.samples) == 1:
            artifacts.append(artifact)
        else:
            for input in artifact.input_artifact_list():
                artifacts.extend(self._get_non_pooled_artifacts(input))

        return artifacts

    def samplesheet(self, flowcell):
        containers = self.get_containers(name=flowcell)

        if containers:
            container = containers[-1] # only take the last one. See ÖA#217.
            raw_lanes = sorted(container.placements.keys())
            for raw_lane in raw_lanes:
                lane = self._get_placement_lane(raw_lane)
                placement_artifact = container.placements[raw_lane]
                for artifact in self._get_non_pooled_artifacts(placement_artifact):
                    sample = artifact.samples[0] # we are assured it only has one sample
                    label = self._get_reagent_label(artifact)
                    index = self._get_index(label)
                    yield {
                        'fcid': flowcell,
                        'lane': lane,
                        'sample_id': sample.id,
                        'sample_ref': SAMPLE_REF,
                        'index': index,
                        'description': '',
                        'sample_name': sample.project.name,
                        'control': 'N',
                        'recipe': 'R1',
                        'operator': 'script',
                        'project': sample.project.name
                    }


class ClinicalLims(Lims, SamplesheetHandler):

    def case(self, customer, family_id):
        filters = {'customer': customer, 'familyID': family_id}
        samples = self.get_samples(udf=filters)
        return samples

    def sample(self, lims_id, is_cgid=False):
        """Get a unique sample from LIMS."""
        if is_cgid:
            udf_key = 'Clinical Genomics ID'
            lims_samples = self.get_samples(udf={udf_key: lims_id})
            if len(lims_samples) == 1:
                return lims_samples[0]
            elif len(lims_samples) > 1:
                matches_str = ', '.join(sample.id for sample in lims_samples)
                message = "'{}' matches: {}".format(lims_id, matches_str)
                raise MultipleSamplesError(message)
            else:
                # no matching samples
                return None
        else:
            lims_sample = Sample(self, id=lims_id)

        return lims_sample

    def is_delivered(self, lims_id):
        """Check if a sample has been delivered."""
        filters = dict(samplelimsid=lims_id, type="Analyte",
                       process_type="CG002 - Delivery")
        delivery_analytes = self.get_artifacts(**filters)
        if delivery_analytes:
            return delivery_analytes[0].parent_process.udf['Date delivered']
        else:
            return None

    def process_samples(lims_process):
        """Retrieve LIMS input samples from a process."""
        for artifact in lims_process.all_inputs():
            for lims_sample in artifact.samples:
                yield {'sample': lims_sample, 'artifact': artifact}

    def get_received_date(self, lims_id):
        lims_artifacts = self.get_artifacts(process_type='CG002 - Reception Control',
                                            samplelimsid=lims_id)
        for artifact in lims_artifacts:
            udf_key = 'date arrived at clinical genomics'
            if artifact.parent_process and artifact.parent_process.udf.get(udf_key):
                return artifact.parent_process.udf.get(udf_key)


def deliver(lims_sample):
    """Figure out how to deliver results for a sample.

    Answers:
        - whether to delivery to Scout
        - where to deliver raw data
        - wether we shoud delivery extra assets
    """
    extras = []
    # should the sample be uploaded in Scout?
    to_scout = 'scout' in lims_sample.udf.get('Data Analysis', 'notFound')
    # we should always deliver at least FASTQ files somewhere, but where?
    # the default is to deliver to Caesar
    payload = {'target': 'caesar'}
    customer = lims_sample.udf['customer']

    uppmax_project = lims_sample.udf.get('uppmax_project')
    if uppmax_project:
        payload = {'target': 'uppmax', 'project': uppmax_project}

    if customer == 'cust002':
        extras.append('bam')
    elif customer == 'cust009':
        # molecular health... "there's a script for that"
        payload = {}
    elif customer in ('cust008', 'cust016', 'cust019', 'cust020'):
        payload = {'target': 'sll-sthlm@medstore.sahlgrenska.gu.se'}
    elif customer == 'cust000':
        payload = {'target': 'rasta'}

    return {
        'scout': to_scout,
        'customer': customer,
        'raw_data': payload,
        'extras': extras
    }
