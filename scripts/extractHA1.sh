#!/usr/bin/env bash

set -u
set -e

seq=$1

# A regular expression that should capture the entire HA1 region
H1_HA_regex="DT[LI]C.*QSR"
H3_HA_regex="QKL.*QTR"
MIN_LENGTH=1500

# make an alignment of all sequences longer than 1500
smof filter -l $MIN_LENGTH $seq | smof translate -f | mafft /dev/stdin > $seq.aln 2> /dev/null

# get the bounds for the H1 region
bounds=$(smof grep -qP --gff  "$H1_HA_regex|$H3_HA_regex" $seq.aln | cut -f4,5 | sort | uniq -c | sort -rg | head -1 | sed 's/ *[0-9]* *//')

smof subseq -b $bounds $seq.aln | smof clean -u > ${seq}_HA1.faa
