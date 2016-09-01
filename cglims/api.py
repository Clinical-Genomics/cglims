# -*- coding: utf-8 -*-
from genologics.entities import Sample
from genologics.lims import Lims

from cglims.exc import MultipleSamplesError


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


def parse_udfs(udfs):
    """Parse raw UDF values for a sample."""
    pass
