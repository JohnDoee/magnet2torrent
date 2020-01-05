import os

from setuptools import find_packages, setup

from magnet2torrent import __version__

def readme():
    with open("README.md") as f:
        return f.read()

setup(
    name="magnet2torrent",
    version=__version__,
    url="https://github.com/JohnDoee/magnet2torrent",
    author="Anders Jensen",
    author_email="johndoee@tridentstream.org",
    description="Turn a bittorrent magnet links into a .torrent file.",
    long_description=readme(),
    long_description_content_type="text/markdown",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["aiohttp==3.6.2",],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Internet :: WWW/HTTP",
    ],
    entry_points={
        "console_scripts": ["magnet2torrent = magnet2torrent.__main__:main",]
    },
)
