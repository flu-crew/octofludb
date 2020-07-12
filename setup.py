from setuptools import setup

from octofludb.version import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="octofludb",
    version=__version__,
    description="Interface to the flu-crew swine surveillance database",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/flu-crew/octofludb",
    author="Zebulun Arendsee",
    author_email="zebulun.arendsee@usda.gov",
    packages=["octofludb"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={"console_scripts": ["octofludb=octofludb.ui:main"]},
    py_modules=["octofludb"],
    zip_safe=False,
    include_package_data=True,
)
