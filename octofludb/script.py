from __future__ import annotations
from typing import Optional, List, Iterable, TypeVar

import hashlib
import subprocess
import yaml
import smof  # type: ignore
import glob
import os
import sys
import shutil
import math
from octofludb.util import log, die
import octofludb.colors as colors

A = TypeVar("A")


def get_data_file(filename: str) -> str:
    return os.path.join(os.path.dirname(__file__), "data", filename)


def octofludbHome() -> str:
    return os.path.join(os.path.expanduser("~"), ".octofludb")


def getDataDir(config: dict) -> str:
    try:
        datadir = expandpath(config["datadir"])[0]
    except IndexError:
        die("Failed to find a data directory (check the octofludb config file)")
    if not os.path.exists(datadir):
        os.mkdir(datadir)
    return datadir


def error_log_entry(entries: Iterable[str], logfile: str) -> str:
    homedir = octofludbHome()
    logdir = os.path.join(homedir, "logs")
    logpath = os.path.join(logdir, logfile)

    if not os.path.exists(logdir):
        os.mkdir(logdir)

    with open(logpath, "a") as f:
        for line in entries:
            print(line, file=f)

    return logpath


def epiflu_fasta_files(config: dict) -> List[str]:
    try:
        data_home = getDataDir(config)
    except KeyError:
        die("The config file is missing a `datadir` entry")
    except IndexError:
        die("The path to the `datadir` entry in config does not exist")

    try:
        epiflu_fasta = config["epiflu_fasta"]
    except KeyError:
        die("The config file is missing a epiflu_fasta field")

    return expandpath(os.path.join(data_home, epiflu_fasta))


def epiflu_meta_files(config: dict) -> List[str]:
    try:
        data_home = getDataDir(config)
    except KeyError:
        die("The config file is missing a `datadir` entry")
    except IndexError:
        die("The path to the `datadir` entry in config does not exist")

    try:
        epiflu_meta = config["epiflu_meta"]
    except KeyError:
        die("The config file is missing an epiflu_meta field")

    return expandpath(os.path.join(data_home, epiflu_meta))


def get_octoflu_reference(config: dict) -> Optional[str]:
    try:
        refpath = config["octoflu_reference"]
        if refpath:
            try:
                reference = expandpath(os.path.join(octofludbHome(), refpath))[0]
            except IndexError:
                die(
                    "The octoflu_reference file specified in the octofludb config does not exist"
                )
        else:
            reference = None
    except KeyError:
        die("The config file is missing a `datadir` entry")
    except IndexError:
        die("The path to the `datadir` entry in config does not exist")
    return reference


def tag_files(config: dict, tag: str) -> List[str]:
    try:
        data_home = expandpath(config["datadir"])[0]
    except KeyError:
        die("The config file is missing a `datadir` entry")
    except IndexError:
        die("The path to the `datadir` entry in config does not exist")

    try:
        tagfile = config["tags"][tag]
    except KeyError:
        die(f"Could not find tag {tag} in config")

    return expandpath(os.path.join(data_home, tagfile))


def initialize_config_file() -> str:
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


def load_config_file() -> dict:
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
    return config


def file_md5sum(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def evenly_divide(total: int, preferred_size: int) -> List[int]:
    n = max(math.ceil(total / preferred_size), 1)
    size = total // n
    return [size + (i < total - size * n) for i in range(n)]


def partition(xs: List[A], sizes: List[int]) -> List[List[A]]:
    xss = []
    start = 0
    for size in sizes:
        if start >= len(xs):
            break
        else:
            xss.append(xs[start : start + size])
            start += size
    return xss


def runOctoFLU(path: str, reference: Optional[str] = None) -> List[List[str]]:
    """
    Run octoFLU on the given fasta paths.

    OctoFLU mangles names terribly, so it is important to ensure that the input
    names are appropriate segment ids (e.g., genbank ids or epiflu ids).

    Return a list of tuple rows containing octoFLU results
    """

    # The given path may be a glob (e.g., `data/*fna`), so expand to all
    # fasta files and make the paths absolute
    fastafiles = expandpath(path)

    if reference:
        try:
            reference = expandpath(reference)[0]
        except IndexError:
            die(f"The path {reference} does not point to a file")

    # Store the current working directory so that we can return to it at the
    # end of this function
    cwd = os.getcwd()

    def cleanup():
        os.chdir(cwd)

    # List of all files that have been successfully created. These will be
    # concatenated together and uploaded after a successful run.
    created_files = []

    try:

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
            fna = list(smof.uniq_headers(smof.open_fasta(fastafile)))

            if len(fna) == 0:
                next

            # break the input fasta into small pieces so we don't kill our tree builder
            for (i, chunk) in enumerate(partition(fna, evenly_divide(len(fna), 5000))):
                # create a default name for the fasta file chunk
                chunk_relpath = f"x{str(i)}_{os.path.basename(fastafile)}"
                with open(chunk_relpath, "w") as chunk_fh:
                    # write the FastaEntry list to the chunk filename
                    smof.print_fasta(chunk, out=chunk_fh)

                    chunk_fh.flush()

                    # run octoFLU using the given reference
                    try:
                        log(
                            f"Running command: './octoFLU.sh {chunk_relpath}' from '{os.getcwd()}'"
                        )
                        subprocess.run(["./octoFLU.sh", chunk_relpath], check=True)
                    except subprocess.CalledProcessError as e:
                        log(colors.bad(f"`./octoFLU.sh {chunk_relpath}` failed"))
                        raise e
                    # if the octoFLU command was successful, it will have created a table in the location below
                    table_path = os.path.join(
                        f"{chunk_relpath}_output", f"{chunk_relpath}_Final_Output.txt"
                    )
                    # add the absolute path to this table to the created file list
                    created_files.append(expandpath(table_path)[0])

        results = []
        for filename in created_files:
            with open(filename, "r") as f:
                results += [
                    [r.strip() for r in line.split("\t")[0:4]] for line in f.readlines()
                ]

        # move the original reference file back if it was moved
        if reference and os.path.exists("reference.fa~"):
            os.rename("reference.fa~", reference_path)
    except Exception as e:
        cleanup()
        log(colors.bad("octoFLU run failed"))
        raise e

    cleanup()

    return results


def findMotifs(
    sparql_filename: str, patterns: List[str], subtype: str, url: str, repo_name: str
) -> str:
    import octofludb.formatting as formatting
    import pgraphdb as db
    import flutile

    # write fasta file
    fasta_filename = f"{subtype}.fna"
    results = db.sparql_query(
        sparql_file=sparql_filename, url=url, repo_name=repo_name
    ).convert()
    with open(fasta_filename, "w") as f:
        formatting.write_as_fasta(results, outfile=f)

    # use flutile to find motifs
    motif_filename = f"{subtype}-motif.tab"
    flutile.write_bounds(
        tabular=True,
        motif_strs=patterns,
        keep_signal=False,
        subtype=subtype,
        fasta_file=fasta_filename,
        conversion="dna2aa",
        outfile=motif_filename,
    )

    return motif_filename


def cloneGithubRepo(user: str, repo: str) -> None:
    """
    Clone a github repository if the repo folder is not already present.
    """
    if not os.path.exists(repo):
        subprocess.run(["git", "clone", f"http://github.com/{user}/{repo}"])


def buildHome() -> str:
    return os.path.join(octofludbHome(), "build")


def gotoBuildHome() -> None:
    """
    Change directory to the octofldub build folder, create it if it does not exist
    """

    # move to octofludb build home
    build_dir = buildHome()
    if not os.path.exists(build_dir):
        os.mkdir(build_dir)
    print(f"Moving to {build_dir}", file=sys.stderr)
    os.chdir(build_dir)


def expandpath(path: str) -> List[str]:
    """
    Expands globs and gets absolute paths

    This command NEVER fails. If nothing in a path exists, an empty list is returned.
    """
    return glob.glob(os.path.abspath(os.path.expanduser(path)))
