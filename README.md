# UnityPyLive2DExtractor
[![Windows Build](https://github.com/mos9527/UnityPyLive2DExtractor/actions/workflows/python-publish.yml/badge.svg)](https://github.com/mos9527/UnityPyLive2DExtractor/blob/main/.github/workflows/python-publish.yml) 
[![Releases](https://img.shields.io/github/downloads/mos9527/UnityPyLive2DExtractor/total.svg)](https://GitHub.com/mos9527/UnityPyLive2DExtractor/releases/) 
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) 

General purpose [Live2D](https://www.live2d.com/) Asset recovery tool built w/ [UnityPy](https://github.com/K0lb3/UnityPy) and [sssekai](https://github.com/mos9527/sssekai)

As the name suggests, this project is heavily inspired by [Perfare/UnityLive2DExtractor](https://github.com/Perfare/UnityLive2DExtractor). With a few key differences:
- All Live2D types are implemented with [dumped TypeTree](https://github.com/mos9527/UnityPyLive2DExtractor/blob/main/external/typetree_cubism.json) and [generated types](https://github.com/mos9527/UnityPyLive2DExtractor/blob/main/typetree_codegen.py). This should help with compatibility issues.
    - Do note, however, that you may need to update the TypeTree if the Live2D version changes.
    - Generate the TypeTree with [typetree_codegen](https://github.com/mos9527/UnityPyLive2DExtractor/blob/main/typetree_codegen.py) and replace the existing TypeTree at `UnityPyLive2DExtractor/generated`
    ```bash
    python typetree_codegen.py type_tree_cubism.json UnityPyLive2DExtractor/generated
    ```
- New (not necessarily better) asset discovery method. Though proven to be more reliable in some cases.

## Installation
- Install the script from PyPI
```bash
pip install UnityPyLive2DExtractor
```
- Or, you can use the pre-built executables for Windows from [Releases](https://github.com/mos9527/UnityPyLive2DExtractor/releases/).
## Usage
```bash
UnityPyLive2DExtractor <input> <output>
```
Where `<input>` is the path to your game's path, and `<output>` is the directory to extract the Live2D assets to.
## References
- https://github.com/Perfare/UnityLive2DExtractor
- https://github.com/K0lb3/TypeTreeGenerator
- https://github.com/K0lb3/UnityPy