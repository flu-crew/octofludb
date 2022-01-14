import parsec as p
import re

p_A0 = p.regex("A0\d{7}")
p_tosu = p.regex("\d+TOSU\d+")
p_epi_isolate = p.regex("EPI_ISL_\d+")


def clean_strain(x):
    x = x.strip().replace(" ", "_")
    # strain names may be parenthesized:  (A/Bratislava/6/97 (H3N2))
    x = re.sub("^\((.*)\)$", "\\1", x)
    # remove terminal parentheses
    x = re.sub("_*\(.*\)_*$", "", x)
    # remove terminal braces
    x = re.sub("_*\[.*\]_*$", "", x)
    return x


p_strain_no_paren = p.regex("[ABCD]/[^/()\[\]]+/.+").parsecmap(clean_strain)
p_strain_paren = p.regex("\([ABCD]/[^/()\[\]]+/.+\)").parsecmap(clean_strain)
p_strain = p_strain_paren ^ p_strain_no_paren

p_barcode = p_A0 ^ p_tosu ^ p_epi_isolate ^ p_strain  # e.g. A01104095 or 16TOSU4783
p_gb = p.regex("[A-Z][A-Z]?\d{5,7}")
p_epi_id = p.regex("EPI_?\d\d\d+")
p_seqid = p_gb ^ p_epi_id

p_global_clade = (
    p.regex("\d[ABC]([\._-]\d+){1,4}([_-]?like)?([_-]?vaccine)?")
    ^ p.regex("Other-[A-Za-z]*[0-9.a-zA-Z-]*")
    ^ p.regex("3\.[12][09]\d0\.[0-9.a-zA-Z-]+")
    ^ p.regex("(humanVaccine|Outgroup)")
)
