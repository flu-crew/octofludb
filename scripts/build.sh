#!/usr/bin/env bash

set -e
set -u

DATADIR="STATIC"

log() {
    echo "$1" > /dev/stderr
}

mkdir ttl || log "Overwriting files in ttl/"

# file="${DATADIR}/A0_2019-05-15.xlsx"
# log "Loading swine surveillance data from $file"
# time d79 load_excel $file --rdf="ttl/A0.ttl" --format="turtle"
#
#
# file="STATIC/cdc_cvv/strain_ids.txt"
# tag="cdc_cvv"
# log "Loading CDC_CVV strains from '$file' as tag '$tag'"
# time d79 tag "$file" "$tag" --rdf="ttl/$tag.ttl" --format="turtle"
#
#
# file="${DATADIR}/antiserum/strain_ids.txt"
# tag="antiserum"
# log "Loading antisera strains from '$file' as tag '$tag'"
# time d79 tag "$file" "$tag" --rdf="ttl/$tag.ttl" --format="turtle"
#
#
# file="${DATADIR}/global-reference/strain_ids.txt"
# tag="global-reference"
# log "Loading global reference strains from '$file' as tag '$tag'"
# time d79 tag "$file" "$tag" --rdf="ttl/$tag.ttl" --format="turtle"
#
#
# file="${DATADIR}/swine-reference/strain_ids.txt"
# tag="swine-reference"
# log "Loading segment references from '$file' as tag '$tag'"
# time d79 tag "$file" "$tag" --rdf="ttl/$tag.ttl" --format="turtle"
#
#
# file="${DATADIR}/vaccine/strain_ids.txt"
# tag="vaccine"
# log "Loading strain recommended by WHO for vaccines from '$file' as tag '$tag'"
# time d79 tag "$file" "$tag" --rdf="ttl/$tag.ttl" --format="turtle"
#
#
# tag="fair"
# log "Loading fair data from files '${DATADIR}/fair/201[678].xlsx'' as tag '$tag'"
# time d79 load_excel "${DATADIR}/fair/2016.xlsx" --rdf="ttl/fair2016.ttl" --tag="fair" --format="turtle"
# time d79 load_excel "${DATADIR}/fair/2017.xlsx" --rdf="ttl/fair2017.ttl" --tag="fair" --format="turtle"
# time d79 load_excel "${DATADIR}/fair/2018.xlsx" --rdf="ttl/fair2018.ttl" --tag="fair" --format="turtle"
#
#
# file="${DATADIR}/pdm-2019.fasta"
# log "Loading $file"
# time d79 load_fasta "$file" --tag="pdm-2019" --format="turtle" --delimiter="|" --rdf="ttl/pdm-2019.ttl"
#
#
# file="${DATADIR}/influenza_na.dat"
# log "Loading IVR data dump from '$file'"
# time d79 load_strains "$file" --rdf="ttl/influenza_na.ttl" --format="turtle"


# file="${DATADIR}/blast.txt"
# log "Loading blast results from $file"
# time d79 load_blast "$file" --tag="blast" --rdf="ttl/blast.ttl"  --format="turtle"


# ## TODO: push all files to the GraphDB database before running the fetch step
# ## Currently I have to manually stop here, go to the GraphDB browser, and
# ## upload the influenza_na dataset (at least).
# # #
# # # # For now just use the existing swine-ids.txt, it is quite good enough
# # # log "Retrieving all swine Genbank IDs and selected human IDs (saved in gb-id.txt)"
# # # time q79 ~/src/git/d79/turtles/fetch-swine-gids.ttl > gb.ids
log "Compiling Genbank records for each of these IDs"
time d79 load_gbids gb.ids --rdf="ttl/genbank.ttl" --format="turtle"

log $(date)
log "done"
