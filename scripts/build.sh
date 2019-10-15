#!/usr/bin/env bash

set -e
set -u

DATADIR="STATIC"

log() {
    echo "$1" > /dev/stderr
}

mkdir ttl || log "Overwriting files in ttl/"

# file="${DATADIR}/IRD-results.tsv"
# log "Loading global clade data from IRD"
# cut -f12,15 $file | awk 'NR == 1 {print "strain\tglobal_clade"} NR != 1 {print}' > ${file}~
# time d79 load_table ${file}~ > ttl/h1_global_clades.ttl
#
# file="${DATADIR}/A0_all.xlsx"
# log "Loading swine surveillance data from $file"
# time d79 load_table --exclude="proseq,dnaseq" --levels="strain" $file > ttl/A0.ttl
#
# file="${DATADIR}/antiserum/antiserum_ids"
# tag="antiserum"
# log "Loading antisera strains from '$file' as tag '$tag'"
# time d79 tag "$file" --tag="$tag" > ttl/$tag.ttl
#
# file="${DATADIR}/antiserum/antigen_ids"
# tag="antigen"
# log "Loading antigen strains from '$file' as tag '$tag'"
# time d79 tag "$file" --tag="$tag" > ttl/$tag.ttl

file="STATIC/CDC_CVV/CVV.fasta"
tag="cdc_cvv"
log "Loading CDC_CVV strains from '$file' as tag '$tag'"
time d79 load_fasta "$file" --tag="$tag" > ttl/$tag.ttl

file="${DATADIR}/vaccine/strain_ids.txt"
tag="vaccine"
log "Loading strain recommended by WHO for vaccines from '$file' as tag '$tag'"
time d79 tag "$file" --tag="$tag" > ttl/$tag.ttl

file="${DATADIR}/global-reference/strain_ids.txt"
tag="global-reference"
log "Loading global reference strains from '$file' as tag '$tag'"
time d79 tag "$file" --tag="$tag" > ttl/$tag.ttl

file="${DATADIR}/swine-reference/strain_ids.txt"
tag="swine-reference"
log "Loading segment references from '$file' as tag '$tag'"
time d79 tag "$file" --tag="$tag" > ttl/$tag.ttl

file="${DATADIR}/influenza_na.dat"
log "Loading IVR data dump from '$file'"
time d79 load_strains "$file" > ttl/influenza_na.ttl

# TODO: push all files to the GraphDB database before running the fetch step
# Currently I have to manually stop here, go to the GraphDB browser, and
# upload the influenza_na dataset (at least).

# For now just use the existing swine-ids.txt, it is quite good enough
log "Retrieving all swine Genbank IDs and selected human IDs (saved in gb-id.txt)"
time q79 ~/src/git/d79/turtles/fetch-swine-gids.rq > gb.ids

# log "Compiling Genbank records for each of these IDs"
# time d79 load_gbids gb.ids > ttl/genbank.ttl~ && mv ttl/genbank.ttl~ ttl/genbank.ttl

log $(date)
log "done"
