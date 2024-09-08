from setuptools import setup, find_packages

setup(
    name="brightpearl_client",
    version="0.1.0",
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "requests",
        "pydantic",
    ],
    author="Patrick Steil",
    author_email="patrick.steil@infranet.com",
    description="A simple and limited Python client for the BrightPearl API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/pmsteil/brightpearl_client",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        # the MIT license allows for commercial use
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
    ],
)
