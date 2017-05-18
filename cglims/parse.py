# -*- coding: utf-8 -*-


def parse_artifacts(lims, lims_id):
    """Parse artifacts for a sample."""
    data = {}
    artifacts = lims.get_artifacts(samplelimsid=lims_id)
    for artifact in artifacts:
        if artifact.parent_process.type.id == '657':
            # CG002 - Aliquot Samples for Covaris
            data['dna_concentration'] = artifact.udf['Concentration']
        if artifact.parent_process.type.id == '667':
            # CG002 - End repair Size selection A-tailing and Adapter...
            udf_key = 'Lot no: TruSeq DNA PCR-Free Sample Prep Kit'
            data['library_kit_lot_1'] = artifact.parent_process.udf[udf_key]
            data['beads_t1_lot'] = artifact.parent_process.udf['Lot no: SP Beads']

    return data


#     # pre-sequencing lab stuff
#     capture_kit = Column(types.String(32))
#     library_kit_lot_1 = Column(types.String(32))
#     library_kit_lot_2 = Column(types.String(32))
#     # can sometimes be a mix of two kits
#     baits_lot = Column(types.String(64))
#     beads_t1_lot = Column(types.String(32))
#     fragment_size = Column(types.Integer)
#     input_material = Column(types.Float)
#     index_sequence = Column(types.String(32))
