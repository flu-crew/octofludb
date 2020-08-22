#!/usr/bin/env bash

set -u
set -e

log() {
    echo $@ >> log
}

nlines() {
    wc -l $1 | sed 's/ *//' | sed 's/ .*//'
}

log "--" $(date)

test -d octoFLU || git clone https://github.com/flu-crew/octoFLU

dat=DATA
ttl=turtles

octofludb init

function upload(){
    datfile=$dat/$1
    shift
    ttlfile=$ttl/$1
    shift

    log -n "translating $datfile to $ttlfile"

    if [ ! -f ${datfile} ]
    then
        log " ... Cannot find ${datfile}"
        exit 1
    elif [ ${datfile} -nt ${ttlfile} ] || [ ! -f ${ttlfile} ]
    then
        octofludb $@ ${datfile} > ${ttlfile}
        octofludb upload ${ttlfile}
    else
        log " ... skipping"
    echo
    fi
}

mkdir -p "$ttl" 

update-genbank() {
    log "Fetching all influenza genbank ids"

    allgb=.all-gb.ids
    oldgb=.gb-existing.ids
    newgb=.gb-new.ids

    time octofludb query fetch-gids.rq > $allgb

    touch $ttl/genbank.ttl
    grep genbank_id $ttl/genbank.ttl | sed 's/.*"\([^"]*\)".*/\1/' > $oldgb

    # find the genbank ids that are not in the current genbank.ttl file
    comm -1 -3 <(sort $oldgb) <(sort $allgb) > $newgb

    log "Adding $(nlines $newgb) genbank ids to the current set of $(nlines $oldgb)"
    time octofludb mk_gbids $newgb > genbank-new.ttl
    octofludb upload genbank-new.ttl

    cat genbank-new.ttl <(grep -v '^@prefix' $ttl/genbank.ttl) > genbank.ttl~
    mv genbank.ttl~ $ttl/genbank.ttl
    rm -f $allgb $oldgb $newgb
}

function update-epiflu-metadata(){
    data=$1
    turtle=$2
    echo -n "Epiflu ${data} to ${turtle} ... " >> log
    if [ ! -f $turtle ]
    then
        echo "loading" >> log
        octofludb mk_gis $data > $turtle
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
        octofludb mk_fasta $data > $turtle
        octofludb upload $turtle
    else
        echo "skipping" >> log
    fi
}
export -f update-epiflu-fasta

function octoflu(){
    octofludb query --fasta fetch-swine-sequences.rq > .all.fna
    touch $ttl/octoflu.ttl
    smof grep -Xvf <(grep genbank_id $ttl/octoflu.ttl | sed 's/.*genbank_id "\([^"]*\).*/\1/') .all.fna > .new.fna
    rm -f .xxx*
    smof split --number=1000 --seqs --prefix=".xxx"  .new.fna
    rm -rf octoFLU/.xxx*
    mv .xxx* octoFLU
    cd octoFLU
    parallel "./octoFLU.sh {}" ::: .xxx*
    cd ..
    cat octoFLU/.xxx*Final_Output.txt |
        sort -u |
        awk 'BEGIN {OFS="\t"; FS="\t"; print "genbank_id", "clade", "gl_clade"} {print $1, $3, $4}' > .octoflu_results
    octofludb mk_table .octoflu_results > $ttl/octoflu.ttl
    octofludb upload $ttl/octoflu.ttl
}

function constellate(){
    echo "strain_name	constellation" > .const.tab
    octofludb const >> .const.tab
    octofludb mk_table .const.tab > .const.ttl
    rm .const.tab
    mv .const.ttl turtles/constellations.ttl
    octofludb upload turtles/constellations.ttl 
}


function make-tags(){
    list=$1
    tag=$2
    octofludb tag $list $tag > $ttl/$tag.ttl
    octofludb upload $ttl/$tag.ttl
}


upload influenza_na.dat influenza_na.ttl mk_ivr
upload IRD-results.tsv IRD.ttl mk_ird
update-genbank

parallel "update-epiflu-metadata {} ${ttl}/{/}.ttl" ::: ${dat}/epiflu/h*/*xls
parallel "update-epiflu-fasta    {} ${ttl}/{/}.ttl" ::: ${dat}/epiflu/h*/*fasta

octoflu
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
