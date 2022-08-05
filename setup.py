"""dcv"""
import setuptools

__version__ = "1.0.2"
__author__ = "Ryan Gillespie"

setuptools.setup(
    name="dcv",
    version=__version__,
    packages=["dcv"],
    install_requires=["httpx>=0.22.0", "typer>=0.4.1"],
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
    ],
    python_requires=">=3.7",
    entry_points={"console_scripts": ["dcv = dcv.cli:app"]},
)
