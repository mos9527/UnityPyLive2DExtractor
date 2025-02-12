import argparse
import os
from zlib import crc32
import UnityPy
from UnityPy.classes import MonoBehaviour, Texture2D, PPtr
from UnityPy.enums import ClassIDType
from UnityPy.files import ObjectReader
from logging import getLogger
import coloredlogs
from . import __version__


# from UnityPy.helpers import TypeTreeHelper
# TypeTreeHelper.read_typetree_boost = False
logger = getLogger("UnityPyLive2DExtractor")

import UnityPyLive2DExtractor.generated as generated
from .generated.Live2D.Cubism.Core import CubismMoc
import importlib


def read_from(reader: ObjectReader, **kwargs):
    match reader.type:
        case ClassIDType.MonoBehaviour:
            mono: MonoBehaviour = reader.read(check_read=False)
            script = mono.m_Script.read()
            nameSpace = script.m_Namespace
            className = script.m_Name
            if script.m_Namespace:
                fullName = script.m_Namespace + "." + className
            else:
                fullName = className
            typetree = generated.TYPETREE_DEFS.get(fullName, None)

            if typetree:
                result = reader.read_typetree(typetree)
                nameSpace = importlib.import_module(
                    f".generated.{nameSpace}", package=__package__
                )
                clazz = getattr(nameSpace, className, None)
                instance = clazz(**result)
                return instance
            else:
                raise NotImplementedError(className)
        case _:
            return reader.read(**kwargs)


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
        try:
            obj = read_from(reader)
            if type(obj) == CubismMoc:
                print(obj)
        except NotImplementedError as e:
            logger.warning(f"Skipping {e}")
            continue


if __name__ == "__main__":
    __main__()
