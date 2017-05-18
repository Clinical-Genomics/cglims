# -*- coding: utf-8 -*-
import re

SAMPLE_REF = 'hg19'


class SamplesheetHandler(object):

    def _get_placement_lane(self, lane):
        """Parse out the lane information from an artifact.placement"""
        return int(lane.split(':')[0])

    def _get_index(self, label):
        """Parse out the sequence from a reagent label"""

        reagent_types = self.get_reagent_types(name=label)

        if len(reagent_types) > 1:
            raise ValueError("Expecting at most one reagent type. Got ({}).".format(len(reagent_types)))

        reagent_type = reagent_types.pop()
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

        for container in containers:
            raw_lanes = sorted(container.placements.keys())
            for raw_lane in raw_lanes:
                lane = self._get_placement_lane(raw_lane)
                placement_artifact = container.placements[raw_lane]
                for artifact in self._get_non_pooled_artifacts(placement_artifact):
                    # we are assured it only has one sample
                    sample = artifact.samples[0]
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
