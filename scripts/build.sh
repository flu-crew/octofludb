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
octofludb upload ../schema/geography.ttl
octofludb upload ../schema/schema.ttl

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
    octofludb query --fasta fetch-unclassified-swine.rq | smof uniq -f > .all.fna
    rm -f .xxx*
    smof split --number=5000 --seqs --prefix=".xxx"  .all.fna
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
        # awk 'BEGIN {OFS="\t"; FS="\t"} {print $1, $2, $3, $4}' >> .octoflu_results
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

function make-motifs(){
    ./find-motifs.sh
    for motif in Sa Sb Ca1 Ca2 Cb
    do
        awk -v name=${motif}_motif 'BEGIN{OFS="\t"}
            NR == 1 {print "genbank_id", name}
            {print}' ${motif}.tab > .tmp
        octofludb mk_table .tmp > ${motif}.ttl
        octofludb upload ${motif}.ttl 
        mv ${motif}.ttl $ttl/${motif}.ttl
        rm .tmp
        rm ${motif}.tab
    done
}

octofludb update_gb
octofludb upload .gb_*.ttl

parallel "update-epiflu-metadata {} ${ttl}/{/}.ttl" ::: ${dat}/epiflu/h*/*xls
parallel "update-epiflu-fasta    {} ${ttl}/{/}.ttl" ::: ${dat}/epiflu/h*/*fasta

octoflu

# This must be run after octoFLU
octofludb subtypes > .subtype.txt
octofludb mk_table .subtype.txt > .subtype.ttl
octofludb upload .subtype.ttl

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
