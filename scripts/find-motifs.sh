#!/usr/bin/env bash

set -e
set -u

octofludb query --fasta fetch-surveillance-H1.rq | sed 's/ /_/g' > .A0.fna
./extractHA1.sh .A0.fna
HA1=.A0.fna_HA1.faa

for clade in gamma delta1 delta2 alpha pdm beta LAIV_gamma2-beta-like
do
   smof grep $clade .A0.fna_HA1.faa > .A0_$clade.faa
done

function most-common-interval(){
    cut -f4,5 /dev/stdin | sort | uniq -c | sort -rg | head -1 | sed 's/ *[0-9]* *//'
}


# pattern to extract with Sa region - the Sa motif consists of 3 blocks within this pattern
#  1. residues 2-3, which can be extracted by index
#  2. an internal block of 5 residues, since there may be gaps, this region
#  must be extracted using a pattern (SaMotif2)
#  3. the last 6 residues, can be extracted by index
SaMotifWide='WP.*FY.*(KINK|NLSK|[MR]LNI|KL[NS][QK]|KLSK).'
SaMotif2='(KKGNS|[EV]KNGL|VKN[GN]L|[KQ]KGNS|KK[GE]NS|KK[GD]DS)'

SbMotif="[TN]..DQ..LY.[NKT]."

# The three components of the Ca1 motif (with flanking residues)
Ca1_1_motif="Y.N.K.." # 1 flanking residue
Ca1_2_motif="(VG...Y.|V.SSHYS|.GSSKYS)" # 2 flanking residue
Ca1_3_motif="(LLEP.DT|L.EPG..|[IL][VIL].PGD.)" # 2 flanking residue

# As with Ca1
Ca2_1_motif="(C..AG..S|CSH.G..S|C.HAG...)" # 1 flanking
Ca2_2_motif="KVR.Q." # 2 flanking

CbMotif="(LI.[KR].S|L[FS]T..S|L.[RAT]A.S|[LI].TV.S|[LQ]..KES)"



function motif-extraction(){
    motif=$1
    fasta=$2
    bounds=$(smof grep -qgP --gff "$motif" $fasta | most-common-interval)
    smof subseq -b $bounds $fasta
}

function tabulate-motif(){
    smof clean -w 0 /dev/stdin |
        sed 's/|.*//' |
        sed 's/>//' |
        awk 'BEGIN{OFS="\t"} (NR % 2 == 1) { h = $0 } (NR % 2 == 0) { print h, $0 }'
}


function make-Sa-table(){
# Patterns matching the context of Sa
#
# gamma   WP.*FYR.*KINK       2438/4513
# delta1  WP.*FYR.*NLSK       2979/3147
# delta2  WP.*FYR.*NLSK       1417/1499
# alpha   WP.*FYR.*[MR]LNI     543/648
# pdm     WP.*FY..*KL[NS][QK]  624/750
# beta    WP.*FYR.*KLSK        243/256
# LAIV    WP.*FYR.*KLSK         58/59
# -------------------------------------
# WP.*FY.*(KINK|NLSK|[MR]LNI|KL[NS][QK]|KLSK)
#          ^    ^    ^       ^          ^
#  gamma --'    |    |  pdm -'          |
#     delta ----'    |    beta/LAIV ----'
#        alpha ------'
#
# smof grep -qgP --gff 'WP.*FY.*(KINK|NLSK|[MR]LNI|KL[NS][QK]|KLSK)' .A0.fna_HA1.faa > z
# 8378/10763 (127 174)
#   25/10763 (127 276) -- Late hit ... chance sequence convergence (or exotic chimerism)
#    4/10763 ( 79 174) -- Bad hit, due to early WP
#
# cut -f4,5 z | sort | uniq -c | sort -g
#
# Find the most common motifs starting from the pdm motif KKGNS in (Liu2018)
#
# $ smof grep -qgP --gff KKGNS sa-wide.faa | cut -f4,5
# $ smof subseq -b 33 42 sa-wide.faa | smof clean -x | smof grep alpha | grep -v '>' | sort | uniq -c | sort -g
#
# pdm     KKGNS
# delta1  [EV]KNGL
# delta2  VKN[GN]L
# gamma   [KQ]KGNS
# beta    KK[GE]NS
# alpha   KK[GD]DS
# --------------------------------------------------------
#     (KKGNS|[EV]KNGL|VKN[GN]L|[KQ]KGNS|KK[GE]NS|KK[GD]DS)
#      ^     ^        ^         ^       ^        ^
#  pdm-'     |        |  gamma -'       |        |
#    delta1 -'        |     beta -------'        |
#      delta2 --------'                alpha ----'
# -----------------------------------------------------------------
    ### collect the three Sa segments
    motif-extraction "$SaMotifWide" $HA1 > sa-wide.faa
    smof subseq -b 2 3 sa-wide.faa | smof clean -x | tabulate-motif > Sa-1.tab
    motif-extraction "$SaMotif2" sa-wide.faa | smof clean -x | tabulate-motif > Sa-2.tab
    smof grep -Pgqo '.{6}$' sa-wide.faa | smof clean -x | tabulate-motif > Sa-3.tab

    # make final table
    join -1 1 -2 1 <(sort Sa-1.tab) <(sort Sa-2.tab) |
        join -1 1 -2 1 /dev/stdin <(sort Sa-3.tab) | sed 's/ /	/' | sed 's/ /-/g' | sort -u > Sa.tab

    # clean up
    rm Sa-* sa-wide.faa
}




######## finding Sb ##################
# # Step 1: find the interval of the exact motif used in Liu2018
# BOUNDS=$(smof grep --gff -gq TTADQQSLYQNA $HA1 | most-common-interval)

# Step 2: for each H1 clade, find a motif that captures the diversity well(ish)
function check-motif(){
    clade=$1
    motif=$2
    bounds=$3
    smof grep "$clade" $HA1 > .tmp
    smof subseq -b $bounds .tmp | grep -v '>' | sort | uniq -c | sort -g
    echo $(smof grep -qgP "$motif" .tmp | grep -c '>') "/" $(smof wc -l .tmp)
    # smof grep --gff -qgP "$motif" .tmp | cut -f 4,5 | uniq -c
    rm .tmp
}

BOUNDS="201 212"
# check-motif alpha 'T[SEGD]NDQ[QRK]WLY[QK]N[AT]' "$BOUNDS"
 #   9 T S    NDQ Q   WLY Q  N A
 #  11 T G    NDQ R   WLY Q  N A
 #  16 T E    NDQ Q   WLY Q  N A
 #  19 T G    NDQ Q   WLY K  N A
 #  21 T D    NDQ Q   WLY Q  N A
 #  47 T G    NDQ R   WLY Q  N T
 #  97 T G    NDQ K   WLY Q  N A
 # 374 T G    NDQ Q   WLY Q  N A
 #     |      |||     ||| :  | :
 #     T[SEGD]NDQ[QRK]WLY[QK]N[AT]
 # 602/648
# check-motif beta  'T[NDS]TDQQ[TAS]LYQNA' "$BOUNDS"
 #  10 T N   TDQQ T   LYQNA
 #  31 T D   TDQQ A   LYQNA
 #  56 T S   TDQQ S   LYQNA  -- LAIV
 # 104 T[NDS]TDQQ[TAS]LYQNA
# check-motif gamma  'TS[ATDVN]DQ[QR][ST][LI]Y[KQR]N[SEAT]' "$BOUNDS"
 #   20 TS A     DQ Q  S   L   Y K   N S
 #   20 TS N     DQ Q  S   L   Y Q   N A
 #   22 TS A     DQ Q  S   I*  Y K   N A -- * this is the only example of an non-Leucine here
 #   25 TS A     DQ Q  S   L   Y K   N T
 #   27 TS A     DQ Q  S   L   Y R   N A
 #   32 TS V     DQ Q  S   L   Y Q   N A
 #   44 TS A     DQ Q  T   L   Y K   N A
 #   78 TS A     DQ Q  S   L   Y K   N E
 #  119 TS T     DQ Q  S   L   Y K   N A
 #  222 TS D     DQ R  S   L   Y Q   N A
 #  242 TS T     DQ Q  S   L   Y Q   N A
 # 1570 TS A     DQ Q  S   L   Y Q   N A
 # 1761 TS A     DQ Q  S   L   Y K   N A
 # -------------------------
 #      TS[ATDVN]DQ[QR][ST][LI]Y[KQR]N[SEAT]
 # 4218/4513
# check-motif delta2  'N[MI][GERK]DQ[RK][AT]LY[HRN][KT]E' "$BOUNDS"
 #  10 N I   G    DQ R   A  LY H    K  E
 #  10 N M   E    DQ R   T  LY R    T  E
 #  14 N I   G    DQ R   A  LY H    T  E
 #  14 N I   R    DQ K   A  LY N    T  E
 #  16 N I   E    DQ R   A  LY H    K  E
 #  16 N M   K    DQ R   A  LY H    T  E
 #  32 N I   G    DQ K   A  LY H    T  E
 #  48 N I   E    DQ K   A  LY H    T  E
 #  61 N I   E    DQ R   A  LY R    T  E
 #  66 N M   E    DQ R   A  LY R    T  E
 #  78 N M   E    DQ R   A  LY N    T  E
 #  92 N M   G    DQ R   A  LY H    T  E
 # 266 N I   E    DQ R   A  LY H    T  E
 # 652 N M   E    DQ R   A  LY H    T  E
 #     | :        || :   :  ||      :  |
 #     N[MI][GERK]DQ[RK][AT]LY[HRN][KT]E
 # 1442/1499
# check-motif delta1  'N[MI][GERK]DQ[RK][AT]LY[HRN][KT]E' "$BOUNDS"
 #  27 N  I E    T   Q R   T  LY H    T   E
 #  28 N  I G    D   Q R   T  LY N    T   E
 #  37 N  I R    D   Q R   T  LY H    T   E
 #  39 N  I E    N   Q R   T  LY N    K   E
 #  45 N  I E    D   Q R   T  LY H    T   E
 #  64 D  I E    N   Q R   T  LY R    K   D
 #  67 N  I E    N   Q R   T  LY R    T   E
 #  67 N  I G    D   Q R   A  LY H    T   E
 # 110 N  I G    D   Q K   T  LY H    T   E
 # 250 D  I E    N   Q R   T  LY R    K   E
 # 978 N  I G    D   Q R   T  LY H    T   E
 # 983 N  I E    N   Q R   T  LY H    T   E
 #     :  |          |     :  ||      :   :
 #    [DN]I[GER][TDN]Q[RK][TA]LY[HNR][KT][DE]
# check-motif pdm  'T[TINS][VAT][DA]Q[QE][ST]LY[QK]NA' "$BOUNDS"
 #   6 T S     V    D  Q Q   S  LY Q  NA
 #   8 T N     A    D  Q Q   S  LY Q  NA
 #   8 T S     A    D  Q Q   T  LY K  NA
 #  10 T T     T    D  Q Q   S  LY Q  NA
 #  12 T I     T    D  Q Q   S  LY Q  NA
 #  15 T I     A    A* Q E   S  LY Q  NA -- the only non-D
 #  21 T I     A    D  Q Q   S  LY Q  NA
 # 131 T S     A    D  Q Q   S  LY Q  NA
 # 463 T T     A    D  Q Q   S  LY Q  NA
 #     |            :  | :   :  || :  ||
 #     T[TINS][VAT][DA]Q[QE][ST]LY[QK]NA
 # 681/750

# Step 3 - from the clade patterns, build a generic pattern

# beta    T    [NDS]   T       D    Q Q     [TAS] L    Y Q     N     A
# delta1  N    [MI]    [GERK]  D    Q [RK]  [AT]  L    Y [HRN] [KT]  E
# delta2  N    [MI]    [GERK]  D    Q [RK]  [AT]  L    Y [HRN] [KT]  E
# gamma   T    S       [ATDVN] D    Q [QR]  [ST]  [LI] Y [KQR] N     [SEAT]
# pdm     T    [TINS]  [VAT]   [DA] Q [QE]  [ST]  L    Y [QK]  N     A
# alpha   T    [SEGD]  N       D    Q [QRK] W     L    Y [QK]  N     [AT]
# -------------------------------------------------------------------------
#         [TN] .       .       D    Q .     .     L    Y .     [NKT] .
#
# This motif probably contains enough information. The [DA] in pdm and [LI] in
# gamma are sufficiently rare variants that they can be ignored in the broad
# pattern.

# # Step 4 - check how well the generic pattern works
#
# smof grep -cqP "$SbMotif" $HA1
# smof wc -l $HA1
#
# # 8950/10763 match
#
# smof grep --gff -qP "$SbMotif" $HA1 | cut -f 4,5 | sort | uniq -c | sort -g
#
# # All hits are to the region 201-212, perfect specificity



####### Ca1 ###################################################################

# Ca1 is, like Sa, composed of three units. But this time, I will look for each
# component independently. Since the units are a bit small by themselves, I
# will expand the surrounding context by 1 for INDKG and 2 for TSG and EPG. I
# will trim them down afterwards.

# # Step 1: start with the PDM sequence INDKG-TSR-EPG, find the pdm regions where
# # each of the three pieces occur
# Ca1_1=$(smof grep pdm $HA1 | smof grep -qgoP --gff "INDKG" | most-common-interval)
# Ca1_2=$(smof grep pdm $HA1 | smof grep -qgoP --gff "TSR"   | most-common-interval)
# Ca1_3=$(smof grep pdm $HA1 | smof grep -qgoP --gff "EPG"   | most-common-interval)
# echo "$Ca1_1 $Ca1_2 $Ca1_3"

#### These are derived from the data, see above code
#### Currently I am manually adding to them, since arithmetic is murder in bash
# Ca1_1="176 188" # add 1 residue above and below
# Ca1_2="218 224" # add 2 residue above and below
# Ca1_3="250 256" # add 2 residue above and below

function check-Ca1-motif(){
    clade=$1
    m1=$2
    m2=$3
    m3=$4

    echo $clade $m1 $m2 $m3
    echo "------ Ca1_1 ------"
    check-motif $clade "$m1" "$Ca1_1"

    echo "------ Ca1_2 ------"
    check-motif $clade "$m2" "$Ca1_2"

    echo "------ Ca1_3 ------"
    check-motif $clade "$m3" "$Ca1_3"
}


# check-Ca1-motif pdm "YINDKGK"    "VG[ST]S[RK]YS"   "L[IV][DE]PGDK"
# # ------ Ca1_1 ------
# #    2 YFN------DKGK
# #    2 YIN------DKGX
# #    3 YIN------DKEK
# #    8 YVN------DKGK
# #   13 YIN------DKRK
# #   15 YIN------NKGK
# #   17 YTN------DKGK
# #  690 YIN------DKGK *
# #      | |       | |
# #      YIN------DKGK
# #
# # ------ Ca1_2 ------
# #    2 VE T  S R  YS
# #    2 VG K  S R  YS
# #    2 VG T  S R  YN
# #   14 VG S  S R  YS *
# #   52 VG T  S K  YS *
# #  678 VG T  S R  YS *
# #      |     |    |
# #      VG[ST]S[RK]YS
# #
# # ------ Ca1_3 ------
# #    2 L V   E  XGDK
# #    2 L V   K  PGDK
# #    2 L V   X  PGDK
# #    2 L X   E  PRDK
# #    3 L X   E  PGDK
# #    4 V V   E  PGDK
# #    8 I V   E  PGDK
# #    8 X V   E  PGDK
# #   17 L V   D  PGDK *
# #   23 L I   E  PGDK *
# #  679 L V   E  PGDK *
# #      |        ||||
# #      L[IV][DE]PGDK
#
#
# check-Ca1-motif alpha "YVN[DNS][KR][KRG]K" "VGTSTYS" "[IL][VL][EK]PGD[KT]"
# # ------ Ca1_1 ------
# #    1 YVN D   R R   K
# #    2 XVN X   K R   K
# #    2 YIN N   K G   K
# #    2 YIN X   K R   K
# #    2 YVN N   R R   K
# #    5 YIN N   K R   K
# #   13 YVN N   K K   K
# #   13 YVN S   K R   K
# #   22 YVN N   R G   K
# #   33 YVN D   K R   K *
# #  107 YVN D   K G   K
# #  156 YVN N   K G   K
# #  290 YVN N   K R   K
# #      | |
# #      YVN[DNS]K[KRG]K
# #
# # ------ Ca1_2 ------
# #    1 VGSSKYS
# #    2 VGTSAYS
# #    2 VGTSKYS
# #    2 VGTSTYN
# #  641 VGTSTYS
# #      ||:|:|:
# #      VGTSTYS
# #
# #    3 218	224
# # ------ Ca1_3 ------
# #    1 L   I   E  PGDT
# #    1 L   I   K  PGDT
# #    1 L   V   E  PGDE
# #    2 I   V   K  PGDK
# #    2 L   V   E  XGDT
# #    2 X   L   E  PGDT
# #   20 L   V   K  PGDK *
# #   22 L   L   E  PGDT
# #   47 I   V   E  PGDT
# #   72 L   V   K  PGDT
# #  478 L   V   E  PGDT
# #                 |||
# #     [IL][VL][EK]PGD[KT]
#
#
# check-Ca1-motif beta "Y[ISTVL]NNK[KET][KR]" "[VI]GSSKYS" "[IL][VI][DE]PGDT"
# # ------ Ca1_1 ------
# #    1 Y T     N------NK E    K
# #    2 L T     NCTSGRVHH K    K
# #    2 Y I     N------DK K    K
# #    2 Y L     N------NQ K    K
# #    5 Y L     N------NK K    K
# #    6 Y V     N------NK K    K
# #    8 Y I     N------NK T    K
# #    8 Y T     N------NK K    K
# #   13 Y I     N------NK K    R
# #   29 Y S     N------NK K    K
# #   58 Y I     N------NK E    K
# #  122 Y I     N------NK K    K
# #      :       |      ::      :
# #      Y[ISTVL]N------NK[KET][KR]
# #
# # ------ Ca1_2 ------
# #    2 V  GTSKYS
# #    8 I  GSSKYS *
# #  246 V  GSSKYS
# #      :  |:||||
# #     [VI]GSSKYS
# #
# #  248 218	224
# # ------ Ca1_3 ------
# #    1 L   V   D  PGDT
# #    2 I   I   E  PEDT
# #    2 I   V   E  PGDT
# #    2 L   I   E  PGET
# #    2 L   I   K  PGDT
# #    2 L   L   E  PGDT
# #    2 L   V   E  XGDT
# #    2 M   I   E  PGDT
# #    2 V   I   D  PGDT
# #    2 X   I   E  PGDT
# #   22 L   I   D  PGDT *
# #   55 L   V   E  PGDT
# #   72 I   I   E  PGDT
# #   88 L   I   E  PGDT
# #          :      |::|
# #     [IL][VI][DE]PGDT
#
#
# check-Ca1-motif gamma "Y[TI]N[DN]K[KEG][RKMNE]" "VG[ST][SP][RK]Y[SNGN]" "L[IV]EPG[DE][KT]"
# # ------ Ca1_1 ------
# #   ... (skipping some)
# #   22 Y I  N D  K E    K
# #   30 Y I  N N  R E    K
# #   30 Y T  N N  K K    K
# #   32 Y I  N N  K E    E
# #   67 Y I  N N  K G    K
# #  100 Y I  N N  K E    M
# #  103 Y I  N N  K E    N
# #  106 Y I  N D  K E    R
# #  169 Y T  N N  K G    K
# #  207 Y I  N N  K K    K
# #  229 Y T  N N  K E    K
# # 3271 Y I  N N  K E    K
# #      |    |    |
# #      Y[TI]N[DN]K[KEG][RKMNE]
# #
# # ------ Ca1_2 ------
# #    4 VG S   S   K  Y N
# #    5 VG S   S   R  Y G
# #    6 VG S   X   R  Y S
# #    8 VG S   S   R  Y X
# #   16 VG T   S   R  Y S
# #   18 VG S   S   R  Y N
# #   26 VG T   S   K  Y S
# #   73 VG S   P   R  Y S
# # 1040 VG S   S   K  Y S
# # 3304 VG S   S   R  Y S
# #      ||            |
# #      VG[ST][SP][RK]Y[SNGN]
# #
# # 4386 218	224
# # ------ Ca1_3 ------
# #   ........
# #   10 L V  EPG D   M
# #   12 L V  EPG D   E
# #   16 L L  EPG D   K
# #   23 L V  EPG G   K
# #   30 L V  KPG D   K
# #   34 L V  EXG D   K
# #   50 L V  EPG D   R
# #   56 I V  EPG D   K
# #   63 L V  EPG E   K
# #   71 L V  EPG D   T
# #  162 L I  EPG D   K
# # 3935 L V  EPG D   K
# #      |    :|| :   :
# #      L[IV]EPG[DE][KT]
#
#
# check-Ca1-motif delta1 "Y[KE]N[DE]K[EG]K" "V[TAIMV]SSHYS" "LLEPGDT"
# # ------ Ca1_1 ------
# #      ...
# #   54 Y E  N N  K E  K
# #   75 Y E  N N  K G  K
# #  174 Y K  N N  K E  K
# #  235 Y K  N D  K G  K
# #  260 Y K  N E  K G  K
# #  310 Y K  N D  K E  K
# #  909 Y E  N D  K G  K
# #  912 Y E  N D  K E  K
# #      |    |    |    |
# #      Y[KE]N[DE]K[EG]K
# #
# # ------ Ca1_2 ------
# #      ...
# #   39 V I     SSHYS
# #   90 V T     SSHYS
# #  304 V A     SSHYS
# # 1175 V M     SSHYS
# # 1471 V V     SSHYS
# #      |       |||||
# #      V[TAIMV]SSHYS
# #
# # ------ Ca1_3 ------
# #      ...
# #   20 LLEPEDT
# #   30 LLEPGDK
# #   32 LLEPRDT
# #   40 LLKPGDT
# #   45 LLAPGDT
# #   51 LLEPGET
# # 2869 LLEPGDT *
# #      ||:|:::
# #      LLEPGDT
#
#
# check-Ca1-motif delta2 "YTN[KD][REK][EG]K" "VVSSHYS" "LLEP[GRE]DT"
# # ------ Ca1_1 ------
# #      ...
# #   28 YTN D   K    E  K
# #   31 YTN K   K    G  K
# #   42 YTN K   R    E  K
# #   89 YTN K   E    E  K
# #  282 YTN K   E    G  K
# #  959 YTN K   K    E  K
# #      |||             |
# #      YTN[KD][REK][EG]K
# #
# # ------ Ca1_2 ------
# #      ...
# #   14 VVTSHYS
# # 1454 VVSSHYS
# #      ||:||||
# #      VVSSHYS
# #
# # ------ Ca1_3 ------
# #      ...
# #   25 MLEP G   DT
# #   48 LLEP R   DT
# #   83 LLEP E   DT
# # 1318 LLEP G   DT
# #      :|||     ||
# #      LLEP[GRE]DT


# Ca1-1
# alpha    Y V       N [DNS] K     [KRG] K           YVN.K.K
# beta     Y [ISTVL] N N     K     [KET] [KR]        Y.NNK..
# delta1   Y [KE]    N [DE]  K     [EG]  K           Y.N.K.K
# delta2   Y T       N [KD]  [REK] [EG]  K           YTN...K
# gamma    Y [TI]    N [DN]  K     [KEG] [RKMNE]     Y.N.K..  <-- contains every other pattern
# pdm      Y I       N D     K     G     K           YINDKGK
# ----------------------------------------------
# Y.N.K..

# Ca1-2
# alpha    V    G       T    S    T    Y S         VGTSTYS
# beta     [VI] G       S    S    K    Y S         .GSSKYS
# delta1   V    [TAIMV] S    S    H    Y S         V.SSHYS  <-- contains delta2
# delta2   V    V       S    S    H    Y S         VVSSHYS
# gamma    V    G       [ST] [SP] [RK] Y [SNGN]    VG...Y.  <-- contains the pdm and alpha patterns
# pdm      V    G       [ST] S    [RK] Y S         VG.S.YS
# ----------------------------------------------
# (VG...Y.|V.SSHYS|.GSSKYS)
#  ^       ^       ^       
#  gamma   delta*  beta    
#  pdm                     
#  alpha                   

# Ca1-3
# alpha    [IL] [VL] [EK] P G     D    [KT]      ...PGD.  <-- contains beta, delta1 and pdm
# beta     [IL] [VI] [DE] P G     D    T         ...PGDT
# delta1   L    L    E    P G     D    T         LLEPGDT 
# delta2   L    L    E    P [GRE] D    T         LLEP.DT
# gamma    L    [IV] E    P G     [DE] [KT]      L.EPG..
# pdm      L    [IV] [DE] P G     D    K         L..PGDK
# ----------------------------------------------
# (LLEP.DT|L.EPG..|[IL][VIL].PGD.)
#  ^       ^       ^
#  delta2  gamma   alpha / beta / delta1 / pdm
#
# smof grep -gP --gff "...PGD." $HA1 | cut -f4,5 | sort | uniq -c
# # the "...PGD." motif has a large number of incorrect hits (to the 92-98
# # interval), so need to add additional information.
#
# # Check goodness:
# smof grep -gP --gff $Ca1_1_motif $HA1 | cut -f4,5 | sort | uniq -c
# smof grep -gP --gff $Ca1_2_motif $HA1 | cut -f4,5 | sort | uniq -c
# smof grep -gP --gff $Ca1_3_motif $HA1 | cut -f4,5 | sort | uniq -c
#
# Out of 10763:
# -------------
# 10159 176 188    10159/10763 match to the right location
#     3 169 175    3 mismatch
#                  the rest have no match (which is fine)
#
# 10643 218 224
#     2 241 247
#     2  76  82
#
# 10617 250 256

function make-Ca1-table(){
    motif-extraction "$Ca1_1_motif" $HA1 | tabulate-motif > Ca1_1.tab
    motif-extraction "$Ca1_2_motif" $HA1 | tabulate-motif > Ca1_2.tab
    motif-extraction "$Ca1_3_motif" $HA1 | tabulate-motif > Ca1_3.tab

    # make final table
    join -1 1 -2 1 <(sort Ca1_1.tab) <(sort Ca1_2.tab) |
        join -1 1 -2 1 /dev/stdin <(sort Ca1_3.tab) |
        sed 's/-*//g' |
        sort -u |
        sed 's/\([^ ]*\) .\([A-Z]*\). ..\([A-Z]*\).. ..\([A-Z]*\)../\1	\2-\3-\4/' | sort -u > Ca1.tab

    # clean up
    rm Ca1_*
}



####### Ca2 ###################################################################
# pdm ref: PHAGAK RD

# Ca2_1_bound=$(smof grep pdm $HA1 | smof grep --gff -qgP "PHAGAK" | most-common-interval)
# # 142 148
# Ca2_2_bound=$(smof grep pdm $HA1 | smof grep --gff -qP "RD" | most-common-interval)
# # 238 239   -- NOTE: will vary depending on the alignment gap positions
Ca2_1_bound="141 149"
Ca2_2_bound="236 241"

function check-Ca2-motif(){
    clade=$1
    m1=$2
    m2=$3

    echo "check-Ca2-motif $clade $m1 $m2"
    echo "------ Ca2_1 ------"
    check-motif $clade "$m1" "$Ca2_1_bound"
    echo

    echo "------ Ca2_2 ------"
    check-motif $clade "$m2" "$Ca2_2_bound"
    echo
}


# check-Ca2-motif alpha "CP[DY]AG..S" "KV[RK][GD]Q[SAT]"
# # ------ Ca2_1 ------
# #      ...
# #   10 CP D  AGKSS
# #   14 CP Y  AGRRS
# #   15 CP D  AGKNS
# #   15 CP Y  AGKRS
# #   17 CP D  AGANS
# #   18 CP Y  AGKGS
# #   26 CP D  AGTSS
# #   32 CP Y  AGASS
# #   46 CP Y  AGESS
# #   66 CP Y  AGKSS
# #   74 CP Y  AGRGS
# #  254 CP D  AGASS
# #      ||    ||  |
# #      CP[DY]AG..S
#
# # ------ Ca2_2 ------
# #      ...
# #    8 KV R   G  Q S
# #   19 KV R   D  Q A
# #   21 KV K   G  Q A
# #   26 KV R   D  Q T
# #  212 KV R   G  Q A
# #  343 KV R   G  Q T
# #      ||        |
# #      KV[RK][GD]Q[SAT]
#
# check-Ca2-motif beta "KVR.Q." "C..AGA.S"
# # ------ Ca2_1 ------
# #      ...
# #    4 CSYAGANS
# #    8 CPHAGASS
# #    8 CPYAGAKS
# #   34 CPYAGASS
# #  193 CPYAGANS
# #      |  ||| |
# #      C..AGA.S
#
# # ------ Ca2_2 ------
# #    1 KVRXQA
# #    2 KVRNQE
# #    2 KVRNQT
# #   28 KVRNQA
# #  223 KVRDQA
# #      ||| |
# #      KVR.Q.
#
# check-Ca2-motif delta1 "CSHNG..S" "KVR[DN]QE"
# # ------ Ca2_1 ------
# #      ...
# #   10 CPHNGEGS
# #   10 CPHNGERS
# #   10 CSHNGEXS
# #   12 CPHNGNGS
# #   14 CSYNGER-
# #   15 CSHNGGRS
# #   16 CSHNGGGS
# #   19 CSHKGESS
# #   19 CSHNGKKS
# #   19 CSYKGKSS
# #   19 CSYNGEK-
# #   22 CSHKGEAS
# #   24 CPHNGKGS
# #   29 CSNNGGRN *
# #   48 CSHKGERS
# #   48 CSHKGKSS
# #   93 CSHNGEKS
# #  111 CSHNGESS
# #  190 CSHNGKSS
# #  282 CSHNGEGS
# #  324 CSHNGKRS
# #  572 CSHNGKGS
# # 1021 CSHNGERS
# #      |
# #      CSHNG..S
#
# # ------ Ca2_2 ------
# #    5 KVR D  QR
# #    6 EVR N  QK
# #    6 KLR N  QE
# #    6 KVR D  QG
# #    6 KVR X  QE
# #   15 RVR D  QE
# #   38 KVR D  QK
# #   56 KIR D  QE
# #   67 KVR G  QE
# #  597 KVR N  QE
# # 2306 KVR D  QE
# #      ::|    |:
# #      KVR[DN]QE
#
#
# check-Ca2-motif delta2 "CSH[NK]G.[RS]S" "KVR[DN]Q."
# # ------ Ca2_1 ------
# #    7 CSH N  GN R  S
# #    8 CSH N  GE S  S
# #    8 CSH N  GT S  S
# #    8 CSH S  GN S  S
# #   12 CSH K  GQ S  S
# #   12 CSH N  GQ S  S
# #   18 CSH N  GS S  S
# #   20 CSH N  GK R  S
# #   35 CSH K  GN S  S
# #   96 CSH N  GK S  S
# # 1249 CSH N  GN S  S
# #      |||    |     |
# #      CSH[NK]G.[RS]S
#
# # ------ Ca2_2 ------
# #    6 KVK N  QE
# #    7 KVR N  QR *
# #    8 KVR N  QA
# #   41 KVR D  QE
# #  144 KVR N  QG
# # 1274 KVR N  QE
# #      ||:    |
# #      KVR[DN]Q.
#
#
# check-Ca2-motif gamma "C.HAG..S" "KVRDQ."
# # ------ Ca2_1 ------
# #   10 CHHAGTNS
# #   10 CPHAGTXS
# #   12 CPHVGTKS
# #   16 CSHAGTKS
# #   18 CYHAGTNS
# #   19 CAHAGMRS
# #   23 CSHAGTRS
# #   28 CPHAGTRS
# #   37 CPHDGTNS
# #   39 CPHVGTNS
# #   43 CPHAGANS
# #   50 CPYAGANS
# #   62 CSHAGTNS
# #  126 CPHAGTSS *
# #  360 CPHAGTKS
# # 3496 CPHAGTNS
# #      |   |  |
# #      C.HAG..S
#
# # ------ Ca2_2 ------
# #   10 KVXDQA
# #   16 KVRDQE
# #   23 KVRDQS
# #   28 KVRNQA
# #   88 KVRDQT
# # 4294 KVRDQA
# #      ||| |
# #      KVRDQ.
#
#
# check-Ca2-motif pdm "C.HAGA.." "KVR.QE"
# # ------ Ca2_1 ------
# #    6 CPHAGTKS
# #    6 CPRAGTKS
# #    8 CPYAGAKS
# #   14 CPYAGARS
# #   18 CPHAGAKG
# #   23 CPHAGARS
# #   46 CSHAGAKS
# #  603 CPHAGAKS
# #      |  ||
# #      C.HAGA..
#
# # ------ Ca2_2 ------
# #    2 KVRDQK
# #    2 KVRXQE
# #    4 KVRDQG
# #    4 KVRXXE
# #    6 KVREQE
# #   16 KVRNQE
# #  716 KVRDQE
# #      ||| |:
# #      KVR.QE


# alpha    C P [DY] A    G . .    S    CP.AG..S \  C..AG..S
# beta     C . .    A    G A .    S    C..AGA.S /___________
# delta1   C S H    N    G . .    S    CSHNG..S \  CSH.G..S
# delta2   C S H    [NK] G . [RS] S    CSH.G..S /___________
# gamma    C . H    A    G . .    S    C.HAG..S \  C.HAG...
# pdm      C . H    A    G A .    .    C.HAGA.. /
# ---------------------------------
# (C..AG..S|CSH.G..S|C.HAG...)

# alpha    K V [RK] [GD] Q [SAT]    KV..Q.
# beta     K V R    .    Q .        KVR.Q.
# delta1   K V R    [DN] Q E        KVR.QE
# delta2   K V R    [DN] Q .        KVR.Q.
# gamma    K V R    D    Q .        KVRDQ.
# pdm      K V R    .    Q E        KVR.QE
# -------------------------------
# KVR.Q.

# # Check goodness:
# smof grep -gP --gff $Ca2_1_motif $HA1 | cut -f4,5 | sort | uniq -c
# # 10304 141       149
# smof grep -gP --gff $Ca2_2_motif $HA1 | cut -f4,5 | sort | uniq -c
# # 10561 236       241

function make-Ca2-table(){
    motif-extraction "$Ca2_1_motif" $HA1 | tabulate-motif > Ca2_1.tab
    motif-extraction "$Ca2_2_motif" $HA1 | tabulate-motif > Ca2_2.tab

    # make final table
    join -1 1 -2 1 <(sort Ca2_1.tab) <(sort Ca2_2.tab) |
        sed 's/-*//g' |
        sort -u |
        sed 's/\([^ ]*\) .\([A-Z]*\). ..\([A-Z]*\)../\1	\2-\3/' | sort -u > Ca2.tab

    # clean up
    rm Ca2_*
}



####### Cb ####################################################################
# pdm ref: LSTASS

Cb_bound=$(smof grep pdm $HA1 | smof grep --gff LSTASS | most-common-interval)

function check-cb(){
    clade=$1
    motif=$2
    echo check-cb $clade $motif
    check-motif $clade $motif "$Cb_bound"
}

# check-cb alpha "[LI][LF]TV[NS]S"
# #    5  T   L  TV S  S
# #    6  I   F  TV S  S
# #    8  I   F  TV N  S
# #   18  L   F  TV S  S
# #   24  I   L  TV N  S
# #  569  I   L  TV S  S
# #              ||    |
# #      [LI][LF]TV[NS]S
#
# check-cb beta "L[FS]T.[RS]S"
# #    5 L S  TV S  S
# #    8 L S  TA R  S
# #   17 L F  TR R  S
# #   34 L F  TT S  S
# #  173 L F  TA S  S
# #      |    |     |
# #      L[FS]T.[RS]S
#
# check-cb gamma "L[SA][RAT]A[SRN]S"
# #      ...
# #   52 L Y   T   A S   S
# #   53 L F   T   A S   S
# #   65 L S   T   A I   S
# #   73 L S   A   A N   S
# #   90 L Y   A   A N   S
# #  154 L A   R   A S   S
# #  190 L S   T   A N   S
# #  651 L S   T   A R   S
# # 2897 L S   T   A S   S
# #      |         |     |
# #      L[SA][RAT]A[SRN]S
#
# check-cb delta1 "LI[SPF][KR][KEVD]S"
# #   12 LF S    K   K    S
# #   12 LI F    K   E    S
# #   12 LI S    K   D    S
# #   15 LI P    K   E    S
# #   26 LI S    K   V    S
# #   33 LI S    R   K    S
# #   34 LI P    K   K    S
# #  886 LI S    K   E    S
# # 2063 LI S    K   K    S
# #      |                |
# #      LI[SPF][KR][KEVD]S
#
# check-cb delta2 "[LQ][ITN][SP]KES"
# #   10 L   V    S  KES
# #   12 L   S    S  KES
# #   14 L   F    S  KES
# #   22 Q   I    S  KES
# #   30 L   I    P  KES
# #   81 L   N    S  KES
# #  496 L   T    S  KES
# #  806 L   I    S  KES
# #                  |||
# #     [LQ][ITN][SP]KES
#
# check-cb pdm "L[SP][TA]A[SRN]S"
# #    8 L S   A  A S   S
# #   11 L S   T  A N   S
# #   20 L P   T  A S   S
# #  195 L S   T  A R   S
# #  500 L S   T  A S   S
# #      |        |     |
# #      L[SP][TA]A[SRN]S

# alpha   [LI] [LF]  T     V    [NS]   S    ..TV.S
# beta    L    [FS]  T     .    [RS]   S    L.T..S
# delta1  L    I     [SPF] [KR] [KEVD] S    LI...S
# delta2  [LQ] [ITN] [SP]  K    E      S    [LQ]..KES
# gamma   L    [SA]  [RAT] A    [SRN]  S    L..A.S
# pdm     L    [SP]  [TA]  A    [SRN]  S    L..A.S
# --------------------------------------
# (LI.[KR].S|L[FS]T..S|L.[RAT]A.S|[LI].TV.S|[LQ]..KES)
#    ^          ^        ^             ^      ^
#  delta1     beta    gamma/pdm     alpha    delta2
#
# # # Check goodness:
# smof grep -gP --gff $CbMotif $HA1 | cut -f4,5 | sort | uniq -c


make-Sa-table
motif-extraction "$SbMotif" $HA1 | tabulate-motif > Sb.tab
make-Ca1-table
make-Ca2-table
motif-extraction "$CbMotif" $HA1 | tabulate-motif > Cb.tab
