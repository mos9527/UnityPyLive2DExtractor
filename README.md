# UnityPyLive2DExtractor
General purpose, single-file Unity [Live2D](https://www.live2d.com/) Asset recovery tool built w/ [UnityPy](https://github.com/K0lb3/UnityPy) and [sssekai](https://github.com/mos9527/sssekai)

As the name suggests, this project is heavily inspired by [Perfare/UnityLive2DExtractor](https://github.com/Perfare/UnityLive2DExtractor). With a few key differences:
- All Live2D types that pretains to the asset recovery process are properly implemented. This should help with compatibility issues.
- New (not necessarily better) asset discovery method. Though proven to be more reliable in some cases.

## Installation
- Install the script from PyPI
    - It's **highly** recommended that you install it in a virtual environment. (e.g. via `pipx`).
    - Since as of now, the script only supports `"sssekai<=0.3.12", "UnityPy<1.20"`
```bash
pipx install UnityPyLive2DExtractor
```
- Or, you can use the pre-built executables for Windows from [Releases](https://github.com/mos9527/UnityPyLive2DExtractor/releases/).
## Usage
```bash
UnityPyLive2DExtractor <input> <output>
```
Where `<input>` is the path to your game's path, and `<output>` is the directory to extract the Live2D assets to.
## References
- https://github.com/Perfare/UnityLive2DExtractor