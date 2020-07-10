
v0.1.0
======

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
