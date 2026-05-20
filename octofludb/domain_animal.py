import parsec as p
import re
from typing import Optional


def clean_host(x:Optional[str])->Optional[str]:
    x = re.sub(";.*", "", x.strip().lower()) # type: ignore
    if "scrofa" in x:
        x = "swine"
    elif "pig" in x and "pigeon" not in x:
        x = "swine"
    elif "porcine" in x:
        x = "swine"
    elif "boar" in x:
        x = "swine"
    elif "sapiens" in x:
        x = "human"
    # cannot contain digits
    x = re.findall("^[^0-9]{3,}$|$", x)[0] # type:ignore 
    # avoid matching clades
    bad_match = re.findall("(alpha|beta|^C?_?IV|classical|gamma|seasonal|other|LAIV|pandemic|pdm|TRIG)", x, re.IGNORECASE)
    if len(bad_match) > 0:
        x = None
    x = None if x == "" else x
    return x


p_host = clean_host #p.regex(re.compile("swine|human", re.IGNORECASE))
