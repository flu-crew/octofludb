#!/usr/bin/env bash

set -e
set -u

DATADIR="STATIC"

log() {
    echo "$1" > /dev/stderr
}

mkdir ttl || log "Overwriting files in ttl/"

file="${DATADIR}/IRD-results.tsv"
log "Loading global clade data from IRD"
time d79 load_ird ${file} > ttl/ird.ttl

# TODO: remove this, it is currently needed only for constellations, but I should infer those outside
file="${DATADIR}/A0_all.xlsx"
log "Loading swine surveillance data from $file"
time d79 load_table --exclude="proseq,dnaseq" --levels="strain" $file > ttl/A0.ttl

for a0file in ${DATADIR}/a0/*
do
    echo "Loading $a0file"
    base=$(echo $a0file | sed 's/.tab//' | sed 's;.*/;;')
    d79 load_table $a0file > ttl/a0_${base}.ttl
done

file="${DATADIR}/antiserum/antiserum_ids"
tag="antiserum"
log "Loading antisera strains from '$file' as tag '$tag'"
time d79 tag "$file" --tag="$tag" > ttl/$tag.ttl

file="${DATADIR}/antiserum/antigen_ids"
tag="antigen"
log "Loading antigen strains from '$file' as tag '$tag'"
time d79 tag "$file" --tag="$tag" > ttl/$tag.ttl

file="STATIC/CDC_CVV/CVV.fasta"
tag="cdc_cvv"
log "Loading CDC_CVV strains from '$file' as tag '$tag'"
time d79 load_fasta "$file" --tag="$tag" > ttl/$tag.ttl

file="${DATADIR}/vaccine/strain_ids.txt"
tag="vaccine"
log "Loading strain recommended by WHO for vaccines from '$file' as tag '$tag'"
time d79 tag "$file" --tag="$tag" > ttl/$tag.ttl

file="${DATADIR}/variants/strain_ids.txt"
tag="variants"
log "Loading variants from '$file' as tag '$tag'"
time d79 tag "$file" --tag="$tag" > ttl/$tag.ttl

file="${DATADIR}/global-reference/strain_ids.txt"
tag="global-reference"
log "Loading global reference strains from '$file' as tag '$tag'"
time d79 tag "$file" --tag="$tag" > ttl/$tag.ttl

file="${DATADIR}/swine-reference/strain_ids.txt"
tag="octoflu-reference"
log "Loading octoflu references from '$file' as tag '$tag'"
time d79 tag "$file" --tag="$tag" > ttl/$tag.ttl

file="${DATADIR}/influenza_na.dat"
log "Loading IVR data dump from '$file'"
time d79 load_ivr "$file" > ttl/influenza_na.ttl

TODO: push all files to the GraphDB database before running the fetch step
Currently I have to manually stop here, go to the GraphDB browser, and
upload the influenza_na dataset (at least).

# clean cache
rm .gb*

# For now just use the existing swine-ids.txt, it is quite good enough
log "Retrieving all swine Genbank IDs and selected human IDs (saved in gb-id.txt)"
time q79 ~/src/git/d79/turtles/fetch-swine-gids.rq > gb.ids

log "Compiling Genbank records for each of these IDs"
time d79 load_gbids gb.ids > ttl/genbank.ttl~ && mv ttl/genbank.ttl~ ttl/genbank.ttl

log $(date)
log "done"
