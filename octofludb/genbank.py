from octofludb.nomenclature import uidgen, P, O, make_property, make_uri
from octofludb.util import rmNone, make_maybe_add
from octofludb.hash import chksum
from rdflib import Literal
import sys


def add_gb_meta_triples(g, gb_meta):
    accession = str(gb_meta["GBSeq_primary-accession"])

    gid = make_uri(accession)
    g.add((gid, P.gb, Literal(accession)))

    maybe_add = make_maybe_add(g, gb_meta, gid)
    maybe_add(P.gb_length, "GBSeq_locus")
    maybe_add(P.gb_length, "GBSeq_length")
    maybe_add(P.gb_strandedness, "GBSeq_strandedness")
    maybe_add(P.gb_moltype, "GBSeq_moltype")
    maybe_add(P.gb_topology, "GBSeq_topology")
    maybe_add(P.gb_division, "GBSeq_division")
    maybe_add(P.gb_update_date, "GBSeq_update-date")
    maybe_add(P.gb_create_date, "GBSeq_create-date")
    maybe_add(P.gb_definition, "GBSeq_definition")
    maybe_add(P.gb_primary_accession, "GBSeq_primary_accession")
    maybe_add(P.gb_accession_version, "GBSeq_accession-version")
    maybe_add(P.gb_source, "GBSeq_source")
    maybe_add(P.gb_organism, "GBSeq_organism")
    maybe_add(P.gb_taxonomy, "GBSeq_taxonomy")

    seq = gb_meta["GBSeq_sequence"].upper()
    g.add((gid, P.dnaseq, Literal(seq)))
    g.add((gid, P.chksum, Literal(chksum(seq))))

    igen = uidgen(base=accession + "_feat_")
    for feat in gb_meta["GBSeq_feature-table"]:
        fid = next(igen)
        g.add((gid, P.has_feature, fid))
        g.add((fid, P.name, Literal(feat["GBFeature_key"])))

        maybe_add = make_maybe_add(g, feat, fid)
        maybe_add(P.gb_location, "GBFeature_location")
        #  maybe_add(P.gb_key, "GBFeature_intervals") # for laters

        if "GBFeature_quals" in feat:
            for qual in feat["GBFeature_quals"]:
                if qual["GBQualifier_name"] == "translation":
                    aaseq = qual["GBQualifier_value"]
                    g.add((fid, P.proseq, Literal(aaseq)))
                    g.add((fid, P.chksum, Literal(chksum(aaseq))))
                elif "GBQualifier_name" in qual and "GBQualifier_value" in qual:
                    g.add(
                        (
                            fid,
                            make_property(qual["GBQualifier_name"]),
                            Literal(qual["GBQualifier_value"]),
                        )
                    )
