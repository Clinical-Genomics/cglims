# -*- coding: utf-8 -*-
from genologics.entities import Sample
from genologics.lims import Lims

from cglims.exc import MultipleSamplesError
from .samplesheet import SamplesheetHandler


def connect(config):
    """Connect and return API reference."""
    api = ClinicalLims(config['host'], config['username'], config['password'])
    return api


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
