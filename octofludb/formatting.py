def write_as_fasta(results):
    """
    Write a SPARQL query result as a FASTA file
    """
    header_fields = results["head"]["vars"][:-1]
    seq_field = results["head"]["vars"][-1]
    for row in results["results"]["bindings"]:
        fields = []
        for f in header_fields:
            if f in row:
                fields.append(row[f]["value"])
            else:
                fields.append("")
        header = "|".join(fields)
        sequence = row[seq_field]["value"]
        print(">" + header)
        print(sequence)


def write_as_table(results, header=True):
    """
    Write a SPARQL query result as a TAB-delimited table with an optional header
    """

    def val(xs, field):
        if field in xs:
            return xs[field]["value"]
        else:
            return ""

    if header:
        print("\t".join(results["head"]["vars"]))
    for row in results["results"]["bindings"]:
        fields = (val(row, field) for field in results["head"]["vars"])
        print("\t".join(fields))
