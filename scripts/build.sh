#!/usr/bin/env bash

DB=.d79.db

# load big table from IVR, with roughly the following format:
# (gb | host | ? | subtype | date | ? | "Influenza A virus (<strain>(<subtype>))" | ...)
d79 load_strains $DB "STATIC/influenza_na.dat"

# label CDC_CVV strains
d79 tag_strains $DB "STATIC/cdc_cvv/strain_ids.txt" "cdc_cvvs"

# label antisera strains
d79 tag_strains $DB "STATIC/antiserum/strain_ids.txt" "antiserum"

# label global references, including avian flu examples
d79 tag_strains $DB "STATIC/global-reference/strain_ids.txt" "global-references"

# label reference segments (HA, NA, and internal genes)
d79 tag_strains $DB "STATIC/swine-reference/strain_ids.txt" "swine-reference"

# label strains recommended by WHO for vaccines
d79 tag_strains $DB "STATIC/vaccine/strain_ids.txt" "vaccine"

# load fair data
d79 load_excel $DB "STATIC/fair/2016.xlsx" --event="fair"
d79 load_excel $DB "STATIC/fair/2017.xlsx" --event="fair"
d79 load_excel $DB "STATIC/fair/2018.xlsx" --event="fair"
