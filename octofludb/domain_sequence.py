import parsec as p
import re

p_dnaseq = p.regex(re.compile("[ATGC_RYSWKMBDHVN-]+", re.IGNORECASE))
p_proseq = p.regex(re.compile("[ACDEFGHIKL_MNPQRSTVWX*Y-]+", re.IGNORECASE))
