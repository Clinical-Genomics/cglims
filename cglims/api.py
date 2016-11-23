# -*- coding: utf-8 -*-
from genologics.entities import Sample
from genologics.lims import Lims

from cglims.exc import MultipleSamplesError


def connect(config):
    """Connect and return API reference."""
    api = ClinicalLims(config['host'], config['username'], config['password'])
    return api


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
