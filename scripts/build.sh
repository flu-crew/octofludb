#!/usr/bin/env bash

set -e
set -u

log() {
    echo "$1" > /dev/stderr
}

mkdir ttl || log "Overwriting files in ttl/"

file="STATIC/influenza_na.dat"
log "Loading IVR data dump from '$file'"
time d79 load_strains "$file" --rdf="ttl/influenza_na.ttl" --format="ntriples"


file="STATIC/cdc_cvv/strain_ids.txt"
tag="cdc_cvv"
log "Loading CDC_CVV strains from '$file' as tag '$tag'"
time d79 tag_strains "$file" "$tag" --rdf="ttl/$tag.ttl" --format="ntriples"


file="STATIC/antiserum/strain_ids.txt"
tag="antiserum"
log "Loading antisera strains from '$file' as tag '$tag'"
time d79 tag_strains "$file" "$tag" --rdf="ttl/$tag.ttl" --format="ntriples"


file="STATIC/global-reference/strain_ids.txt"
tag="global-reference"
log "Loading global reference strains from '$file' as tag '$tag'"
time d79 tag_strains "$file" "$tag" --rdf="ttl/$tag.ttl" --format="ntriples"


file="STATIC/swine-reference/strain_ids.txt"
tag="swine-reference"
log "Loading segment references from '$file' as tag '$tag'"
time d79 tag_strains "$file" "$tag" --rdf="ttl/$tag.ttl" --format="ntriples"


file="STATIC/vaccine/strain_ids.txt"
tag="vaccine"
log "Loading strain recommended by WHO for vaccines from '$file' as tag '$tag'"
time d79 tag_strains "$file" "$tag" --rdf="ttl/$tag.ttl" --format="ntriples"


event="fair"
log "Loading fair data from files 'STATIC/fair/201[678].xlsx'' as event '$event'"
time d79 load_excel "STATIC/fair/2016.xlsx" --rdf="ttl/fair2016.ttl" --event="fair" --format="ntriples"
time d79 load_excel "STATIC/fair/2017.xlsx" --rdf="ttl/fair2017.ttl" --event="fair" --format="ntriples"
time d79 load_excel "STATIC/fair/2018.xlsx" --rdf="ttl/fair2018.ttl" --event="fair" --format="ntriples"


file="STATIC/glycosylation-project/glycosylation.xlsx"
event="glyco-project"
log "Loading glycosylation (Todd Davis) project from '$file' as event '$event'"
time d79 load_excel $file --rdf="ttl/glyco-project.ttl" --event=$event --format="ntriples"

### TODO: push all files to the GraphDB database before running the fetch step
### Currently I have to manually stop here, go to the GraphDB browser, and
### upload the influenza_na dataset (at least).

log "Retrieving all swine Genbank IDs and selected human IDs (saved in gb-id.txt)"
time q79 ~/src/git/d79/turtles/fetch-swine-gids.ttl > swine-ids.txt


log "Compiling Genbank records for each of these IDs (this will take a few hours)"
time d79 load_gbids swine-ids.txt --rdf="ttl/genbank.ttl" --format="ntriples"


file="STATIC/blast.txt"
log "Loading blast results from $file"
time d79 load_blast "$file" --event="blast_all-against-all" --rdf="ttl/blast_all-against-all.ttl"  --format="ntriples"

log $(date)
log "done"
