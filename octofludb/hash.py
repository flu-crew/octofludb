from hashlib import md5


def chksum(x):
    chksum = md5()
    chksum.update(bytes(str(x).strip().upper().encode("ascii")))
    return chksum.hexdigest()
