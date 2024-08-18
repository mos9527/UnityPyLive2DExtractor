# UnityPyLive2DExtractor
General purpose, single-file Unity [Live2D](https://www.live2d.com/) Asset recovery tool built w/ [UnityPy](https://github.com/K0lb3/UnityPy) and [sssekai](https://github.com/mos9527/sssekai)

As the name suggests, this project is heavily inspired by [Perfare/UnityLive2DExtractor](https://github.com/Perfare/UnityLive2DExtractor). With a few key differences:
- All Live2D types that pretains to the asset recovery process are properly implemented. This should help with compatibility issues.
- New (not necessarily better) asset discovery method. Though proven to be more reliable in some cases.

## Installation
- Install the script from PyPI
```bash
pip install UnityPyLive2DExtractor
```
- Alternatively, you can also download/copy-paste the script from [`__main__.py`](https://github.com/mos9527/UnityPyLive2DExtractor/blob/main/UnityPyLive2DExtractor/__main__.py) and run it as is, with requisite dependency (i.e. `sssekai`) installed. Python 3.10+ Required.
- Or, you can use the pre-built executables for Windows from [Releases](https://github.com/mos9527/UnityPyLive2DExtractor/releases/)
## Usage
```bash
UnityPyLive2DExtractor <input> <output>
```
Where `<input>` is the path to your game's path, and `<output>` is the directory to extract the Live2D assets to.
## References
- https://github.com/Perfare/UnityLive2DExtractor