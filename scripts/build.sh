#!/usr/bin/env bash

set -u
set -e

log() {
    echo $@ >> log
}

nlines() {
    wc -l $1 | sed 's/ *//' | sed 's/ .*//'
}

dat=DATA
ttl=turtles

function update-epiflu-metadata(){
    data=$1
    turtle=$2
    echo -n "Epiflu ${data} to ${turtle} ... " >> log
    if [ ! -f $turtle ]
    then
        echo "loading" >> log
        octofludb prep gis $data > $turtle
        octofludb upload $turtle
    else
        echo "skipping" >> log
    fi
}
export -f update-epiflu-metadata

function update-epiflu-fasta(){
    data=$1
    turtle=$2
    echo -n "Epiflu ${data} to ${turtle} ... " >> log
    if [ ! -f $turtle ]
    then
        echo "loading" >> log
        octofludb prep fasta $data > $turtle
        octofludb upload $turtle
    else
        echo "skipping" >> log
    fi
}
export -f update-epiflu-fasta

function octoflu(){
    octofludb query --fasta fetch-unclassified-swine.rq | smof uniq -f > .all.fna
    rm -f .xxx*
    smof split --number=5000 --seqs --prefix=".xxx" .all.fna
    rm -rf octoFLU/.xxx*
    mv .xxx* octoFLU
    cd octoFLU
    for file in .xxx*
    do
        ./octoFLU.sh "$file"
    done
    cd ..
    cat octoFLU/.xxx*Final_Output.txt |
        sort -u |
        awk 'BEGIN {OFS="\t"; FS="\t"; print "genbank_id", "segment_subtype", "clade", "gl_clade"} {print $1, $2, $3, $4}' > .octoflu_results
    octofludb prep table .octoflu_results > $ttl/octoflu.ttl
    octofludb upload $ttl/octoflu.ttl
}

function constellate(){
    octofludb make const > .const.tab
    octofludb prep table .const.tab > .const.ttl
    rm .const.tab
    mv .const.ttl turtles/constellations.ttl
    octofludb upload turtles/constellations.ttl 
}


function make-tags(){
    list=$1
    tag=$2
    octofludb prep tag $tag $list > $ttl/$tag.ttl
    octofludb upload $ttl/$tag.ttl
}

function make-motifs(){
    echo "Aligning H1, this may take awhile ..."
    # make H1 motifs
    octofludb query --fasta get-h1-sequences.rq | smof translate -f |
        flutile trim motif \
            --conversion=aa2aa \
            --subtype=H1 \
            -m "Sa=124-125,153-157,159-164" \
            -m "Sb=184-195" \
            -m "Ca1=166-170,203-205,235-237" \
            -m "Ca2=137-142,221-222" \
            -m "Cb=70-75" > .h1-motifs.tab
    octofludb prep table .h1-motifs.tab > $ttl/h1-motifs.ttl

    echo "Aligning H3, this may take awhile ..."
    # make H3 motifs
    octofludb query --fasta get-h3-sequences.rq | smof translate -f |
        flutile trim motif \
            --conversion=aa2aa \
            --subtype=H3 \
            -m "motif=145,155,156,158,159,189" > .h3-motifs.tab
    octofludb prep table .h3-motifs.tab > $ttl/h3-motifs.ttl
}


log "--" $(date)

test -d octoFLU || git clone https://github.com/flu-crew/octoFLU

# you only need to run this once, but it should hurt to run it again
octofludb init
octofludb upload ../schema/geography.ttl
octofludb upload ../schema/schema.ttl

mkdir -p "$ttl"

rm -f .gb_*.ttl
octofludb prep update_gb --nmonths=3
octofludb upload .gb_*.ttl

parallel "update-epiflu-metadata {} ${ttl}/{/}.ttl" ::: ${dat}/epiflu/*/*xls
parallel "update-epiflu-fasta    {} ${ttl}/{/}.ttl" ::: ${dat}/epiflu/*/*fasta

octoflu

# This must be run after octoFLU
octofludb make subtypes > .subtype.txt
grep -v EPI_ISL .subtype.txt > .genbank-subtype.txt
grep -E "strain_name|EPI_ISL" .subtype.txt > .epiflu-subtype.txt

octofludb prep table .genbank-subtype.txt > .genbank-subtype.ttl
octofludb upload .genbank-subtype.ttl

octofludb prep table .epiflu-subtype.txt > .epiflu-subtype.ttl
octofludb upload .epiflu-subtype.ttl

# remove existing constellations and create new ones
octofludb update delete-constellations.rq
constellate

# CVV
make-tags $dat/CDC_CVV/isolate_ids.txt cdc_cvv

# antiserum
make-tags $dat/antiserum/antiserum_strain_names.txt antiserum

# antigen
make-tags $dat/antiserum/antigen_strain_names.txt antigen

# octoflu-references
make-tags $dat/octoflu-references/segment-ids.txt octoflu_refs

# vaccine
make-tags $dat/vaccine/isolate_ids.txt vaccine

# variants
make-tags $dat/variants/isolate_ids.txt variant

# wgs submission
make-tags $dat/wgs/wgs.txt wgs

# add antigenic motifs
make-motifs
