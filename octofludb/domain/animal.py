import parsec as p
import re


def clean_host(x):
    x = re.sub(";.*", "", x.strip().lower())
    if "scrofa" in x:
        x = "swine"
    elif "pig" in x:
        x = "swine"
    elif "porcine" in x:
        x = "swine"
    elif "boar" in x:
        x = "swine"
    elif "sapiens" in x:
        x = "human"
    return x


p_host = p.regex(re.compile("swine|human", re.IGNORECASE))
