# -*- coding: utf-8 -*-
from copy import deepcopy
from dateutil.parser import parse as parse_date

from .apptag import ApplicationTag
from cglims.constants import READS_PER_1X, SEX_MAP


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
