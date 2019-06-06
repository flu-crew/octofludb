#!/usr/bin/env bash

set -e
set -u

log() {
    echo "$1" > /dev/stderr
}

DB=.d79.db

log "Building $DB"


file="STATIC/influenza_na.dat"
log "Loading IVR data dump from '$file'"
time d79 load_strains $DB $file


file="STATIC/cdc_cvv/strain_ids.txt"
tag="cdc_cvv"
log "Loading CDC_CVV strains from '$file' as tag '$tag'"
time d79 tag_strains $DB $file $tag


file="STATIC/antiserum/strain_ids.txt"
tag="antiserum"
log "Loading antisera strains from '$file' as tag '$tag'"
time d79 tag_strains $DB $file $tag


file="STATIC/global-reference/strain_ids.txt"
tag="global-references"
log "Loading global reference strains from '$file' as tag '$tag'"
time d79 tag_strains $DB $file $tag


file="STATIC/swine-reference/strain_ids.txt"
tag="swine-reference"
log "Loading segment references from '$file' as tag '$tag'"
time d79 tag_strains $DB $file $tag


file="STATIC/vaccine/strain_ids.txt"
tag="vaccine"
log "Loading strain recommended by WHO for vaccines from '$file' as tag '$tag'"
time d79 tag_strains $DB $file $tag


event="fair"
log "Loading fair data from files 'STATIC/fair/201[678].xlsx'' as event '$event'"
time d79 load_excel $DB "STATIC/fair/2016.xlsx" --event="fair"
time d79 load_excel $DB "STATIC/fair/2017.xlsx" --event="fair"
time d79 load_excel $DB "STATIC/fair/2018.xlsx" --event="fair"


file="STATIC/glycosylation-project/glycosylation.xlsx"
event="glyco-project"
log "Loading glycosylation (Todd Davis) project from '$file' as event '$event'"
time d79 load_excel $DB $file --event=$event

# log "Retrieving all swine Genbank IDs and selected human IDs (saved in gb-id.txt)"
time ./query.sh ~/src/git/d79/turtles/all-swine-and-refs.ttl > gb-ids.txt
log "Compiling Genbank records for each of these IDs (this will take a few hours)"
time d79 add_gbids $DB gb-ids.txt

log "serializing ..."
d79 serialize $DB dump2.ttl

log $(date)
log "done"
