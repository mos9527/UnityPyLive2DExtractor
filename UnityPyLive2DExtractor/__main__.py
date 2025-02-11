import argparse
import os
import json
import pathlib
import UnityPy
import io
from zlib import crc32
from typing import List
from sssekai.fmt import moc3, motion3
from UnityPy.enums import ClassIDType
from UnityPy.classes import MonoBehaviour, Texture2D, PPtr
from UnityPy.math import Vector2, Vector4
from UnityPy.streams import EndianBinaryReader
from logging import getLogger
import coloredlogs
from . import __version__


from UnityPy.helpers import TypeTreeHelper

TypeTreeHelper.read_typetree_boost = False
logger = getLogger("UnityPyLive2DExtractor")

import UnityPyLive2DExtractor.typetree_generated as generated

from typing import get_type_hints


def evolve_type(clazz: object, d: dict | object):
    """Ignores MRO and initializes the class with the given dictionary recursively

    XXX: Hacky.
    """
    obj = clazz()
    types = clazz.__annotations__
    for k, sub in types.items():
        reduce_arg = getattr(sub, "__args__", [None])[0]
        if isinstance(d[k], list) and hasattr(reduce_arg, "__annotations__"):
            setattr(obj, k, [evolve_type(reduce_arg, x) for x in d[k]])
        elif isinstance(d[k], dict) and hasattr(sub, "__annotations__"):
            setattr(obj, k, evolve_type(sub, d[k]))
        else:
            if isinstance(d[k], dict):
                setattr(obj, k, sub(**d[k]))
            else:
                setattr(obj, k, sub(d[k]))
    return obj


def __main__():
    parser = argparse.ArgumentParser(
        description="UnityPyLive2D Extractor v%d.%d.%d" % __version__
    )
    parser.add_argument("infile", help="Input file/directory to extract from")
    parser.add_argument("outdir", help="Output directory to extract to")
    parser.add_argument(
        "--log-level",
        help="Set logging level",
        default="DEBUG",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument(
        "--no-anim", help="Do not extract animations", action="store_true"
    )
    args = parser.parse_args()
    coloredlogs.install(
        level=args.log_level,
        fmt="%(asctime)s %(name)s [%(levelname).4s] %(message)s",
        isatty=True,
    )
    os.makedirs(args.outdir, exist_ok=True)
    env = UnityPy.load(args.infile)
    for reader in filter(
        lambda reader: reader.type == ClassIDType.MonoBehaviour, env.objects
    ):
        # XXX: Manually mach by Script ClassName
        mono: MonoBehaviour = reader.read(check_read=False)
        script = mono.m_Script.read()
        className = script.m_Name
        if script.m_Namespace:
            fullName = script.m_Namespace + "." + className
        else:
            fullName = fullName
        typetree = generated.TYPETREE_DEFS.get(fullName, None)
        if "Physics" in className:
            pass
        if typetree:
            result = reader.read_typetree(typetree)
            clazz = getattr(generated, className, None)
            instance = evolve_type(clazz, result)
            pass
        else:
            print(f"Unknown type: {className}")
        pass


if __name__ == "__main__":
    __main__()
