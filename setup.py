from setuptools import setup

from octofludb.version import __version__

# Initialize version variable for the linter, it will be assigned when version.py is evaluated
__version__ : str
exec(open('octofludb/version.py', "r").read())

# Read the requirements from the requirements.txt file
with open("requirements.txt", "r") as fh:
    requirements = [r.strip() for r in fh.readlines()]

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="octofludb",
    version=__version__,
    description="Mangage the flu-crew swine surveillance database",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/flu-crew/octofludb",
    author="Zebulun Arendsee",
    author_email="zebulun.arendsee@usda.gov",
    packages=["octofludb"],
    package_data={"octofludb": ["py.typed"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={"console_scripts": ["octofludb=octofludb.ui:main"]},
    install_requires=requirements,
    py_modules=["octofludb"],
    zip_safe=False,
    include_package_data=True,
)
