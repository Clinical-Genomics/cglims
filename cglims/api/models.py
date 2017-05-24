# -*- coding: utf-8 -*-
from cglims.constants import SEX_MAP
from .apptag import ApplicationTag


class Sample(dict):

    """Represent information about a sample in LIMS.

    Args:
        lims_sample (genologics.Sample): the sample instance to extend
    """

    def __init__(self, lims_sample=None):
        self.lims = None
        self.project = None
        self.apptag = None

        if lims_sample:
            self._parse_lims(lims_sample)

    def _parse_lims(self, lims_sample):
        """Parse information that requires a LIMS connection."""
        self.lims = lims_sample
        self._parse_data(lims_sample.id, lims_sample.name, lims_sample.udf)
        self.project = Project(lims_sample.project)

    def _parse_data(self, sample_id, name, udfs):
        """Parse information that doesn't require a LIMS connection."""
        self.update(udfs.items())
        self['id'] = sample_id
        self['name'] = name
        self['old_id'] = self.get('Clinical Genomics ID')
        self['case_id'] = '-'.join([self['customer'], self['familyID']])
        self['sex'] = SEX_MAP.get(self.get('Gender'), None)
        self['exclude_analysis'] = self.get('exclude analysis')
        for parent_id in ['mother', 'father']:
            self[parent_id] = self.get("{}ID".format(parent_id))
        self.apptag = ApplicationTag(self['Sequencing Analysis'])

        gene_panels = set(self['Gene List'].split(';')) if self.get('Gene List') else None
        additional_panel = self.get('Additional Gene List')
        if additional_panel:
            gene_panels.add(additional_panel.strip())
        self['panels'] = list(gene_panels)

    def add_project(self, project_id, name):
        """Add project data manually."""
        self.project = Project()
        self.project._parse_data(project_id, name)

    @property
    def to_analysis(self):
        """Determine if sample is to be analyzed."""
        cancelled = self.get('cancelled') == 'yes'
        tumour = self.get('tumor') == 'yes'
        no_analysis = self.get('exclude analysis') == 'yes'
        return not any([cancelled, tumour, no_analysis])


class Project(dict):

    """Represent a project in LIMS."""

    def __init__(self, lims_project=None):
        self.lims = None

        if lims_project:
            self._parse_lims(lims_project)

    def _parse_lims(self, lims_project):
        """Parse information that require a LIMS connection."""
        self.lims = lims_project
        self._parse_data(lims_project.id, lims_project.name)

    def _parse_data(self, project_id, name):
        """Parse the project."""
        self['id'] = project_id
        self['name'] = name
