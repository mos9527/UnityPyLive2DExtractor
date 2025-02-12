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

from .generated.Live2D.Cubism.Framework.Physics import (
    CubismPhysicsNormalizationTuplet,
    CubismPhysicsNormalization,
    CubismPhysicsParticle,
    CubismPhysicsOutput,
    CubismPhysicsInput,
    CubismPhysicsSubRig,
    CubismPhysicsRig,
    CubismPhysicsController,
)


def monkey_patch(cls):
    """ooh ooh aah aah"""

    def wrapper(func):
        setattr(cls, func.__name__, func)
        return func

    return wrapper


@monkey_patch(CubismPhysicsNormalizationTuplet)
def dump(self: CubismPhysicsNormalizationTuplet):
    return {
        "Maximum": self.Maximum,
        "Minimum": self.Minimum,
        "Default": self.Default,
    }


@monkey_patch(CubismPhysicsNormalization)
def dump(self: CubismPhysicsNormalization):
    return {"Position": self.Position.dump(), "Angle": self.Angle.dump()}


@monkey_patch(CubismPhysicsParticle)
def dump(self: CubismPhysicsParticle):
    return {
        "Position": {"X": self.InitialPosition.x, "Y": self.InitialPosition.y},
        "Mobility": self.Mobility,
        "Delay": self.Delay,
        "Acceleration": self.Acceleration,
        "Radius": self.Radius,
    }


@monkey_patch(CubismPhysicsOutput)
def dump(self: CubismPhysicsOutput):
    return {
        "Destination": {"Target": "Parameter", "Id": self.DestinationId},
        "VertexIndex": self.ParticleIndex,
        "Scale": self.AngleScale,
        "Weight": self.Weight,
        "Type": ["X", "Y", "Angle"][self.SourceComponent],
        "Reflect": self.IsInverted,
    }


@monkey_patch(CubismPhysicsInput)
def dump(self: CubismPhysicsInput):
    return {
        "Source": {"Target": "Parameter", "Id": self.SourceId},
        "Weight": self.Weight,
        "Type": ["X", "Y", "Angle"][self.SourceComponent],
        "Reflect": self.IsInverted,
    }


@monkey_patch(CubismPhysicsSubRig)
def dump(self: CubismPhysicsSubRig):
    return {
        "Input": [x.dump() for x in self.Input],
        "Output": [x.dump() for x in self.Output],
        "Vertices": [x.dump() for x in self.Particles],
        "Normalization": self.Normalization.dump(),
    }


@monkey_patch(CubismPhysicsRig)
def dump(self: CubismPhysicsRig):
    return [
        {"Id": "PhysicsSetting%d" % (i + 1), **rig.dump()}
        for i, rig in enumerate(self.SubRigs)
    ]


@monkey_patch(CubismPhysicsController)
def dump(self: CubismPhysicsController):
    return {
        "Version": 3,
        "Meta": {
            "PhysicsSettingCount": len(self.Rig.SubRigs),
            "TotalInputCount": sum((len(x.Input) for x in self.Rig.SubRigs)),
            "TotalOutputCount": sum((len(x.Output) for x in self.Rig.SubRigs)),
            "VertexCount": sum((len(x.Particles) for x in self.Rig.SubRigs)),
            "Fps": 60,
            "EffectiveForces": {
                "Gravity": {"X": 0, "Y": -1},
                "Wind": {"X": 0, "Y": 0},
            },
            "PhysicsDictionary": [
                {"Id": "PhysicsSetting%d" % (i + 1), "Name": "%d" % (i + 1)}
                for i, _ in enumerate(self.Rig.SubRigs)
            ],
        },
        "PhysicsSettings": self.Rig.dump(),
    }


def read_from(reader: ObjectReader, **kwargs):
    """Import generated classes by MonoBehavior script class type and read from reader"""
    import importlib

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
