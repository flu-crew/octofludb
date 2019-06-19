import parsec as p
import re

p_host = p.regex(re.compile("swine|human", re.IGNORECASE))
