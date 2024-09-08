from setuptools import setup, find_packages

setup(
    name="brightpearl_client",
    version="0.1.0",
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "requests",
        "pydantic",
        "python-dotenv",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python client for the BrightPearl API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/brightpearl_client",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
