import hashlib
import subprocess
import yaml
import pgraphdb
import smof
import glob
import os
from octofludb.classes import Table


def get_data_file(filename):
    return os.path.join(os.path.dirname(__file__), "data", filename)


def octofludbHome():
    return os.path.join(os.path.expanduser("~"), ".octofludb")


def initialize_config_file():
    """
    Create a default config file is none is present in the octofludb home directory
    """
    config_template_file = os.path.join(
        os.path.dirname(__file__), "data", "config.yaml"
    )
    config_local_file = os.path.join(octofludbHome(), "config.yaml")

    if not os.path.exists(config_local_file):
        print(
            f" - Creating config template at '{str(config_local_file)}'",
            file=sys.stderr,
        )
        shutil.copyfile(config_template_file, config_local_file)

    return config_local_file


def load_config_file():
    """
    Load the local config file (create the config file first if it does not exist)
    """
    config_local_file = initialize_config_file()
    with open(config_local_file, "r") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(exc, file=sys.stderr)
            sys.exit(1)


def file_md5sum(path):
    with open(path, "rb") as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    return file_hash


def read_manifest(manifest):
    with open(manifest, "rb") as f:
        hashes = {x.strip() for x in f.readlines()}
    return hashes


def evenly_divide(total, preferred_size):
    n = max(round(total / preferred_size), 1)
    size = total // n
    return [size + (i < total - size * n) for i in range(n)]


def partition(xs, sizes):
    xss = []
    start = 0
    for size in sizes:
        if start >= len(xs):
            break
        else:
            xss.append(xs[start : start + size])
            start += size
    return xss


def runOctoFLU(path, reference=None):
    """
    Run octoFLU on the given fasta paths.

    OctoFLU mangles names terribly, so it is important to ensure that the input
    names are appropriate segment ids (e.g., genbank ids or epiflu ids).
    """

    # Store the current working directory so that we can return to it at the
    # end of this function
    cwd = os.getcwd()

    # List of all files that have been successfully created. These will be
    # concatenated together and uploaded after a successful run.
    created_files = []

    try:
        # The given path may be a glob (e.g., `data/*fna`), so expand to all
        # fasta files and make the paths absolute
        fastafiles = expandpath(path)

        # Everything in this build is relative to the default build directory specified in the config file
        gotoBuildHome()

        # Clone the octoFLU repository IF it is not already present (this
        # command doesn't pull the latest version, that is up to you, I guess).
        cloneGithubRepo("flu-crew", "octoFLU")

        # Move to the octoFLU repo directory
        os.chdir("octoFLU")

        # This is the path to the default reference fasta file
        reference_path = os.path.join("reference_data", "reference.fa")

        # if a reference file is given, copy it over and save the original reference
        if reference:
            # copy the original reference file
            os.rename(reference_path, "reference.fa~")
            shutil.copy(reference, reference_path)

        for fastafile in fastafiles:
            # open the fasta file as a list of FastaEntry objects
            fna = smof.open_fasta(fastafile)
            # break the input fasta into small pieces so we don't kill our tree builder
            for (i, chunk) in enumerate(partition(fna, evenly_divide(len(fna), 5000))):
                # create a default name for the fasta file chunk
                chunk_filename = f"x{str(i)}_{fastafile}"
                # write the FastaEntry list to the chunk filename
                smof.print_fasta(chunk, out=chunk_filename)
                # run octoFLU using the given reference
                subprocess.run(["octoFLU", chunk_filename])
                # if the octoFLU command was successful, it will have created a table in the location below
                table_path = os.path.join(
                    [f"{chunk_filename}_output", f"{chunk_filename}_Final_Output.txt"]
                )
                # add the absolute path to this table to the created file list
                created_files.append(expandpath(table_path))
    except:
        # Ignore any errors? WTF?
        pass

    results = []
    for filename in created_files:
        with open(filename, "r") as f:
            results += [line.split("\t")[0:4] for line in f.readlines()]

    # move the original reference file back if it was moved
    if reference and reref and os.path.exists("reference.fa~"):
        os.rename("reference.fa~", reference_path)

    # move back to wherever we called this command from
    os.chdir(cwd)

    return results


def inferSubtypes(g, url, repo):
    pass
    #  strains, isolates = get_missing_subtypes(url, repo)
    #
    #  for strain_name, subtype in strains:
    #
    #  for isolate_id, subtype in isolates:


def cloneGithubRepo(user, repo):
    """
    Clone a github repository if the repo folder is not already present.
    """
    if not os.path.exists(repo):
        subprocess.run(["git", "clone", f"http://github.com/{user}/{repo}"])


def buildHome():
    return os.path.join(octofludbHome(), "build")


def gotoBuildHome():
    # move to octofludb build home
    build_dir = buildDir()
    if not os.path.exists(build_dir):
        os.mkdir(build_dir)
    os.chdir(build_dir)


def expandpath(path):
    """
    Expands globs and gets absolute paths

    This command NEVER fails. If nothing in a path exists, an empty list is returned.
    """
    return [os.path.abspath(os.path.expanduser(f)) for f in glob.glob(path)]
