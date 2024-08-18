import sys,os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import setuptools, UnityPyLive2DExtractor

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name="UnityPyLive2DExtractor",
    version="%d.%d.%d" % UnityPyLive2DExtractor.__version__,
    author="greats3an",
    author_email="greats3an@gmail.com",
    description="General purpose, single-file Unity Live2D Asset recovery tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mos9527/UnityPyLive2DExtractor",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    install_requires=["sssekai"],
    entry_points={"console_scripts": ["UnityPyLive2DExtractor = UnityPyLive2DExtractor.__main__:__main__"]},
    python_requires=">=3.10",
)