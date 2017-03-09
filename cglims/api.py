# -*- coding: utf-8 -*-
from dateutil.parser import parse as parse_date
from genologics.entities import Sample
from genologics.lims import Lims

from cglims.apptag import ApplicationTag
from cglims.constants import READS_PER_1X, SEX_MAP
from cglims.exc import MultipleSamplesError


def connect(config):
    """Connect and return API reference."""
    api = ClinicalLims(config['host'], config['username'], config['password'])
    return api


class ClinicalSample:

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
        elif self.apptag.is_microbial:
            return 'mwgs'

        return None

    @property
    def sex(self):
        """Return human readable form of sex (Gender)."""
        return SEX_MAP.get(self.udf('Gender'), None)

    @property
    def ordered_reads(self):
        """Calculate ordered number of reads."""
        app_tag = self.udf['Sequencing Analysis']
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

    def udf(self, udf_key, default=None):
        """Get a sample UDF."""
        return self.lims.udf.get(udf_key, default)

    def to_dict(self):
        """Export data from the sample object."""
        if self.udf('customer') and self.udf('familyID'):
            case_id = '-'.join([self.udf('customer'), self.udf('familyID')])
        else:
            case_id = None

        data = {
            'id': self.lims.id,
            # general sample id if imported from old TSL
            'sample_id': self.lims.udf.get('Clinical Genomics ID') or self.lims.id,
            'name': self.lims.name,
            'date_received': parse_date(self.lims.date_received),
            'project_name': self.lims.project.name,
            'sex': self.sex,
            'reads': self.ordered_reads,
            'expected_reads': int(self.ordered_reads * .75),
            'project_id': self.lims.project.id,
            'is_human': self.apptag.is_human,
            'pipeline': self.pipeline,
            'case_id': case_id,
            'panels': (self.udf('Gene List').split(';') if
                       self.udf('Gene List') else None),
        }
        return data


class ClinicalLims(Lims):

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
