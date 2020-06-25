import os

from setuptools import find_packages, setup

def readme():
    with open("README.md") as f:
        return f.read()

setup(
    name="magnet2torrent",
    version="1.1.1",
    url="https://github.com/JohnDoee/magnet2torrent",
    author="Anders Jensen",
    author_email="johndoee@tridentstream.org",
    description="Turn a bittorrent magnet links into a .torrent file.",
    long_description=readme(),
    long_description_content_type="text/markdown",
    license="MIT",
    packages=find_packages("src"),
    package_dir={"":"src"},
    include_package_data=True,
    install_requires=["aiohttp==3.6.*", "six>=1.13.0", "expiringdict>=1.2.0"],
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
