import parsec as p
import re
from src.util import concat

p_A0 = p.regex('A0\d{7}')
p_HA = p.regex('H\d+')
p_NA = p.regex('N\d+')
p_HANA = (p_HA + p_NA).parsecmap(concat)
p_gb = p.regex('[A-Z][A-Z]\d{6}')
p_global = p.regex('\d[ABC](\.\d+){1,4}(_like)?')
p_segment = p.regex('M1|NP|NS1|PA|PB1|PB2|H\d+|N\d+')

# parse state
p_host = p.regex(re.compile("swine"), re.IGNORECASE)
