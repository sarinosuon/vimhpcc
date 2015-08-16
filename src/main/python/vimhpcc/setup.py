from setuptools import setup, find_packages

setup(
    name="vimhpcc",
    version="0.1.0",
    author="Sarino Suon",
    author_email="sarino[dot]suon@yahoo[dot]com",
    url="http://github.com/sarinosuon/vimhpcc/",
    description="executing ECL code on HPCC cluster from vim",
    long_description="Utilities for executing ECL code on HPCC cluster. Includes scala code for calling API",
    scripts = [],
    license = "BSD",
    platforms = ["any"],
    zip_safe=False,
    packages=find_packages()
    )

