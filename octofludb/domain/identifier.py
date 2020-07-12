import parsec as p

p_A0 = p.regex("A0\d{7}")
p_tosu = p.regex("\d+TOSU\d+")
p_epi_isolate = p.regex("EPI_ISL_\d+")
p_strain = p.regex("[ABCD]/[^()\[\]]+").parsecmap(lambda x: x.strip())
p_barcode = p_A0 ^ p_tosu ^ p_epi_isolate ^ p_strain  # e.g. A01104095 or 16TOSU4783

p_gb = p.regex("[A-Z][A-Z]?\d{5,7}")
p_epi_id = p.regex("EPI_?\d\d\d+")
p_seqid = p_gb ^ p_epi_id

p_global_clade = (
    p.regex("\d[ABC]([\._-]\d+){1,4}([_-]?like)?([_-]?vaccine)?")
    ^ p.regex("Other-Human[0-9.ABC-]*")
    ^ p.regex("3\.[12][09]\d0\.[0-9.ABC-]+")
    ^ p.regex("humanVaccine")
)
