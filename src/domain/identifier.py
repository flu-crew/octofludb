import parsec as p

p_A0 = p.regex("A0\d{7}")
p_tosu = p.regex("\d+TOSU\d+")
p_gisaid_isolate = p.regex("EPI_ISL_\d+")
p_strain = p.regex("[ABCD]/[^()\[\]]+")
p_barcode = p_A0 ^ p_tosu ^ p_gisaid_isolate ^ p_strain  # e.g. A01104095 or 16TOSU4783

p_gb = p.regex("[A-Z][A-Z]?\d{5,7}")
p_gisaid_seqid = p.regex("EPI_?\d+")
p_seqid = p_gb ^ p_gisaid_seqid

p_global_clade = p.regex("\d[ABC]([\._]\d+){1,4}(_?like)?")
