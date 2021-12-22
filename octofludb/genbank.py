from octofludb.nomenclature import (
    uidgen,
    P,
    O,
    make_property,
    make_uri,
    make_date,
    make_country_uri,
    make_usa_state_uri,
)
from octofludb.util import rmNone, make_maybe_add
from octofludb.hash import chksum
from rdflib import Literal
from rdflib.namespace import XSD
import re
import octofludb.domain.identifier as identifier
import octofludb.domain.flu as flu
import octofludb.domain.animal as animal
import sys
from octofludb.util import log
from octofludb.colors import bad
import octofludb.domain.geography as geo


def add_gb_meta_triples(g, gb_meta, only_influenza_a=True):
    """
    Add genbank triples

    Parameters
    ----------
    g : rdflib Graph object
    gb_meta : Genbank metadata dictionary from Bio.Entrez
    only_influenza_a : bool

    Returns
    -------
    string containing any raised error or warning message
    """

    error_entry = ""

    try:
        accession = str(gb_meta["GBSeq_primary-accession"])
    except:
        log(bad("Bad Genbank Entry"))
        return "Unknown\tNo primary accession"

    if only_influenza_a:
        # ignore this entry if the organism is not specified
        if not "GBSeq_organism" in gb_meta:
            return f"{accession}\tNo organsim specified"
        # ignore this entry if the organism is not an Influenza virus
        if not bool(re.match("Influenza [ABCD] virus", gb_meta["GBSeq_organism"])):
            return f"{accession}\tNot influenza"

    gid = make_uri(accession)
    g.add((gid, P.gb, Literal(accession)))

    maybe_add = make_maybe_add(g, gb_meta, gid)

    def make_integer(x):
        return rdflib.Literal(x, datatype=XSD.integer)

    maybe_add(P.gb_locus, "GBSeq_locus")
    maybe_add(P.gb_length, "GBSeq_length", formatter=make_integer)
    maybe_add(P.gb_strandedness, "GBSeq_strandedness")
    maybe_add(P.gb_moltype, "GBSeq_moltype")
    maybe_add(P.gb_topology, "GBSeq_topology")
    maybe_add(P.gb_division, "GBSeq_division")
    maybe_add(P.gb_update_date, "GBSeq_update-date", formatter=make_date)
    maybe_add(P.gb_create_date, "GBSeq_create-date", formatter=make_date)
    maybe_add(P.gb_definition, "GBSeq_definition")
    maybe_add(P.gb_primary_accession, "GBSeq_primary_accession")
    maybe_add(P.gb_accession_version, "GBSeq_accession-version")
    maybe_add(P.gb_source, "GBSeq_source")
    maybe_add(P.gb_organism, "GBSeq_organism")
    maybe_add(P.gb_taxonomy, "GBSeq_taxonomy")

    # usually an entry has sequence, but there are weird exceptions
    if "GBSeq_sequence" in gb_meta:
        seq = gb_meta["GBSeq_sequence"].upper()
        g.add((gid, P.dnaseq, Literal(seq)))
        g.add((gid, P.chksum, Literal(chksum(seq))))

    strain = None
    host = None
    date = None
    country = None

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
                if not ("GBQualifier_name" in qual and "GBQualifier_value" in qual):
                    continue
                key = qual["GBQualifier_name"]
                val = qual["GBQualifier_value"]

                if key == "translation":
                    g.add((fid, P.proseq, Literal(val)))
                    g.add((fid, P.chksum, Literal(chksum(val))))
                elif key == "strain":
                    try:
                        strain = identifier.p_strain.parse(val)
                    except:
                        log(bad("Bad strain name: ") + val)
                        error_entry = f"{val}\tBad strain name"
                        strain = val
                elif key == "collection_date":
                    date = make_date(val)
                elif key == "host":
                    host = val
                elif key == "country":
                    country = re.sub(":.*", "", val)
                elif key == "gene":
                    try:
                        segment_name = flu.p_segment.parse_strict(val)
                        # attach the segment_name to the top-level genbank record, not the feature
                        g.add((gid, P.segment_name, Literal(segment_name)))
                    except:
                        pass
                    # attach the original, unparsed gene name to the feature
                    g.add((fid, make_property(key), Literal(val)))
                else:
                    g.add((fid, make_property(key), Literal(val)))

    # link strain information
    if strain:
        sid = make_uri(strain)
        g.add((sid, P.has_segment, gid))
        g.add((sid, P.strain_name, Literal(strain)))
        if host:
            g.add((sid, P.host, Literal(animal.clean_host(host))))
        if date:
            g.add((sid, P.date, date))
        if country:
            code = geo.country_to_code(country)
            country_uri = make_country_uri(country)
            g.add((sid, P.country, country_uri))
            if code is None:
                # if this is an unrecognized country (e.g., Kosovo) then state
                g.add((country_uri, P.name, Literal(country)))
            if code == "USA":
                fields = strain.split("/")
                for field in fields[1:]:
                    # If this looks like a US state, add it
                    code = geo.state_to_code(field)
                    if code:
                        g.add((sid, P.state, make_usa_state_uri(code)))
                    # If this looks like an A0 number, add it
                    try:
                        A0 = identifier.p_A0.parse_strict(field)
                        g.add((sid, P.barcode, Literal(A0)))
                    except:
                        pass
    else:
        locus = gb_meta["GBSeq_locus"]
        log(bad("Missing strain: ") + locus)
        error_entry = f"{locus}\tNo strain name"

    return error_entry
