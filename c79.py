#!/usr/bin/env python3

"""
control a graphdb database.

Usage:
  c79 list [--url=<url>] 
  c79 make [<config_file>] [--url=<url>]
  c79 delete_repository <repo_name> [--url=<url>]
  c79 upload_data <repo_name> <turtle_file>
  c79 delete_data <repo_name> <turtle_file>
  c79 delete_pattern <repo_name> <sparql_file>

Options:
  -h --help       Show this screen.
  --url <url>     The graphdb base URL [default:"http://localhost:7200"]
"""

import os
import sys
import signal
import requests
from docopt import docopt

def make_repo(config, url):
    headers = {}

    files = {'config': (config, open(config, 'rb')),}

    response = requests.post(f'{url}/rest/repositories', headers=headers, files=files)

    return response


def list_repo(url):
  headers = {'Accept': 'application/json',}

  response = requests.get(f'{url}/rest/repositories', headers=headers)

  return response

def delete_repo(url, repo_name):
  headers = { 'Accept': 'application/json', }
  response = requests.delete(f'{url}/rest/repositories/{repo_name}', headers=headers)
  return response

def delete_data(url, repo_name, turtle_file):
  raise NotImplemented

def upload_data(url, repo_name, turtle_file):
  raise NotImplemented

def delete_pattern(url, repo_name, sparql_file):
  raise NotImplemented

def print_response(response):
   if response.status_code >= 400:
     print(f"ERROR: {response.status_code}: {response.text}", file=sys.stderr)
   else:
     print(response.text)

if __name__ == "__main__":
    if os.name is "posix":
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    args = docopt(__doc__, version="c79 0.1.0")

    if args["--url"]:
        url = args["--url"]
    else:
        url = "http://localhost:7200"

    if args["list"]:
      print_response(list_repo(url=url))

    if args["make"]:
      print_response(make_repo(args["<config_file>"], url=url))

    if args["delete_repository"]:
      print_response(delete_repo(repo_name=args["<repo_name>"], url=url))

    if args["delete_data"]:
      delete_data(url=url, repo_name=args["<repo_name>"], turtle_file=args["<turtle_file>"])

    if args["upload_data"]:
      upload_data(url=url, repo_name=args["<repo_name>"], turtle_file=args["<turtle_file>"])

    if args["delete_pattern"]:
      delete_pattern(url=url, repo_name=args["<repo_name>"], sparql_file=args["<sparql_file>"])
