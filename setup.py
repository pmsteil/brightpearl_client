from setuptools import setup, find_packages

setup(
    name="brightpearl_client",
    version="0.1.12",
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "requests",
        "pydantic",
        "python-dotenv",
    ],
    author="Patrick Steil",
    author_email="patrick@infranet.com",
    description="A Python client for the BrightPearl API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/pmsteil/brightpearl_client",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
    ],
)
