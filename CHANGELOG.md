v0.6.0
======

 * Add options for updating a certain number of months to `update_gb`
 * Add maxyear option to `update_gb`
 * Fix bug in `update_gb` that prevented updating of pre-2000 data
 * Fix handling of segment subtypes
 * Determine strain subtype using octoFLU info

v0.5.1
======

 * in `update_gb` - work backwards through months, not just years

v0.5.0
======

 * new subcommands:
   * `update_gb`: add missing genbank entries
   * `const`: generate constellations for all swine strains
   * `masterlist`: generate the A0 masterlist used in NADC quarterly/annual
     reports and octoflushow

 * cleaner strain name parsing:
   * require two forward slashes
   * remove parenthesis/bracket terms, for example:
        "A/wherever/2020 (H1N1)" --> "A/whereever/2020"
   * replace space with underscores, for example:
        "A/South Dakota/2020" --> ""A/South_Dakota/2020""

 * improved data extraction from genbank records 
   * link parental strains to genbank segment records
   * link strain info to the parental strain, including: 
     * host - with new cleaning
     * country - with new cleaning
     * A0 numbers - for USA strains
     * states - for USA strains
     * collection date - as string literal
   * fix incorrect (s, length, locus) link
   * convert `create_date` from string literal to date
   * convert `update_date` from string literal to date
   * convert `length` from string literal to integer

v0.4.0
======

 * Update patterns for global clades
   * allow "Other-Equine" and such
   * allow lowercase letters after "3.XXXX."

v0.3.0
======

 * Add first recipe - a subcommand for getting all constellations
 * Allow the constellation MIXED and allow X for unknown clades

v0.2.0
======

 * Change default repo name to "octofludb"
 * Replace docopt with argparse
 * Renamed all `load_*` commands to `mk_*`. The commands are not "loading" data
   into the database but only creating turtle files
 * Change name to octofludb
 * Add query and upload subcommands
 * Remove `sameAs` relationship between `Strain` tokens. This relationship was
   equating strain names (e.g. `A/Michigan/288/2019`) with epiflu isolate ids
   (e.g., `EPI_ISL_381463`). However, one strain name may be shared by multiple
   epiflu isloate ids, so the sameAs relationship is incorrect. 

v0.1.0
======

Everything up to the point where the name changed from d79 to octofludb
