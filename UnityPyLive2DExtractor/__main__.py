import argparse
import os, io, json, importlib
from zlib import crc32
import UnityPy
from typing import TypeVar
from UnityPy.classes import (
    MonoBehaviour,
    GameObject,
    Transform,
    PPtr,
    Texture2D,
)
from UnityPy.enums import ClassIDType
from UnityPy.files import ObjectReader
from logging import getLogger
import coloredlogs

T = TypeVar("T")

# from UnityPy.helpers import TypeTreeHelper
# TypeTreeHelper.read_typetree_boost = False
logger = getLogger("UnityPyLive2DExtractor")

from sssekai.fmt.motion3 import to_motion3
from sssekai.fmt.moc3 import read_moc3
from sssekai.unity.AnimationClip import AnimationHelper

from UnityPyLive2DExtractor import __version__

# These are here ONLY for the sake of type hints
from UnityPyLive2DExtractor.generated.Live2D.Cubism.Core import CubismModel
from UnityPyLive2DExtractor.generated.Live2D.Cubism.Rendering import CubismRenderer
from UnityPyLive2DExtractor.generated.Live2D.Cubism.Framework.Physics import (
    CubismPhysicsNormalizationTuplet,
    CubismPhysicsNormalization,
    CubismPhysicsParticle,
    CubismPhysicsOutput,
    CubismPhysicsInput,
    CubismPhysicsSubRig,
    CubismPhysicsRig,
    CubismPhysicsController,
)

from dataclasses import dataclass


@dataclass
class ExtractorConfig:
    generated_module: str = "UnityPyLive2DExtractor.generated"

    @property
    def module(self):
        return __import__(self.generated_module)

    def import_path(self, fullname: str):
        namespace = ".".join(fullname.split(".")[:-1])
        classname = fullname.split(".")[-1]
        cls = importlib.import_module(f".{namespace}", package=self.generated_module)
        cls = getattr(cls, classname)
        return cls


CFG = ExtractorConfig()


def patch_all():
    def monkey_patch(fullname):
        """ooh ooh aah aah"""
        cls = CFG.import_path(fullname)

        def wrapper(func):
            setattr(cls, func.__name__, func)
            return func

        return wrapper

    @monkey_patch("Live2D.Cubism.Framework.Physics.CubismPhysicsNormalizationTuplet")
    def dump(self: CubismPhysicsNormalizationTuplet):
        return {
            "Maximum": self.Maximum,
            "Minimum": self.Minimum,
            "Default": self.Default,
        }

    @monkey_patch("Live2D.Cubism.Framework.Physics.CubismPhysicsNormalization")
    def dump(self: CubismPhysicsNormalization):
        return {"Position": self.Position.dump(), "Angle": self.Angle.dump()}

    @monkey_patch("Live2D.Cubism.Framework.Physics.CubismPhysicsParticle")
    def dump(self: CubismPhysicsParticle):
        return {
            "Position": {"X": self.InitialPosition.x, "Y": self.InitialPosition.y},
            "Mobility": self.Mobility,
            "Delay": self.Delay,
            "Acceleration": self.Acceleration,
            "Radius": self.Radius,
        }

    @monkey_patch("Live2D.Cubism.Framework.Physics.CubismPhysicsOutput")
    def dump(self: CubismPhysicsOutput):
        return {
            "Destination": {"Target": "Parameter", "Id": self.DestinationId},
            "VertexIndex": self.ParticleIndex,
            "Scale": self.AngleScale,
            "Weight": self.Weight,
            "Type": ["X", "Y", "Angle"][self.SourceComponent],
            "Reflect": self.IsInverted,
        }

    @monkey_patch("Live2D.Cubism.Framework.Physics.CubismPhysicsInput")
    def dump(self: CubismPhysicsInput):
        return {
            "Source": {"Target": "Parameter", "Id": self.SourceId},
            "Weight": self.Weight,
            "Type": ["X", "Y", "Angle"][self.SourceComponent],
            "Reflect": self.IsInverted,
        }

    @monkey_patch("Live2D.Cubism.Framework.Physics.CubismPhysicsSubRig")
    def dump(self: CubismPhysicsSubRig):
        return {
            "Input": [x.dump() for x in self.Input],
            "Output": [x.dump() for x in self.Output],
            "Vertices": [x.dump() for x in self.Particles],
            "Normalization": self.Normalization.dump(),
        }

    @monkey_patch("Live2D.Cubism.Framework.Physics.CubismPhysicsRig")
    def dump(self: CubismPhysicsRig):
        return [
            {"Id": "PhysicsSetting%d" % (i + 1), **rig.dump()}
            for i, rig in enumerate(self.SubRigs)
        ]

    @monkey_patch("Live2D.Cubism.Framework.Physics.CubismPhysicsController")
    def dump(self: CubismPhysicsController):
        return {
            "Version": 3,
            "Meta": {
                "PhysicsSettingCount": len(self._rig.SubRigs),
                "TotalInputCount": sum((len(x.Input) for x in self._rig.SubRigs)),
                "TotalOutputCount": sum((len(x.Output) for x in self._rig.SubRigs)),
                "VertexCount": sum((len(x.Particles) for x in self._rig.SubRigs)),
                "Fps": 60,
                "EffectiveForces": {
                    "Gravity": {"X": 0, "Y": -1},
                    "Wind": {"X": 0, "Y": 0},
                },
                "PhysicsDictionary": [
                    {"Id": "PhysicsSetting%d" % (i + 1), "Name": "%d" % (i + 1)}
                    for i, _ in enumerate(self._rig.SubRigs)
                ],
            },
            "PhysicsSettings": self._rig.dump(),
        }

    @monkey_patch("Live2D.Cubism.Rendering.CubismRenderer")
    def __hash__(self: CubismRenderer):
        return self._mainTexture.path_id

    @monkey_patch("Live2D.Cubism.Rendering.CubismRenderer")
    def __eq__(self: CubismRenderer, other: CubismRenderer):
        return self.__hash__() == other.__hash__()


# XXX: Is monkey patching this into UnityPy a good idea?
def read_from(reader: ObjectReader, **kwargs):
    """Import generated classes by MonoBehavior script class type and read from reader"""
    TYPETREE_DEFS = CFG.import_path("TYPETREE_DEFS")
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
            typetree = TYPETREE_DEFS.get(fullName, None)

            if typetree:
                result = reader.read_typetree(typetree)
                clazz = CFG.import_path(fullName)
                instance = clazz(object_reader=reader, **result)
                return instance
            else:
                logger.debug(f"Missing definitions for {fullName}, skipping.")
                return mono
        case _:
            return reader.read(**kwargs)


def read_from_ptr(ptr: PPtr[T], reader: ObjectReader) -> T:
    return read_from(ptr.deref(reader.assets_file))


def __main__():
    parser = argparse.ArgumentParser(
        description="UnityPyLive2D Extractor v%d.%d.%d" % __version__
    )
    parser.add_argument("infile", help="Input file/directory to extract from")
    parser.add_argument("outdir", help="Output directory to extract to")
    parser.add_argument(
        "--module",
        help="Generated Live2D module from TypeTree dump. Read the README for info.",
        default="UnityPyLive2DExtractor.generated",
    )
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
    logger.info("UnityPyLive2D Extractor v%d.%d.%d" % __version__)
    CFG.generated_module = args.module
    patch_all()
    os.makedirs(args.outdir, exist_ok=True)
    logger.info("Loading %s" % args.infile)
    env = UnityPy.load(args.infile)
    objs = [
        read_from(reader)
        for reader in filter(
            lambda reader: reader.type == ClassIDType.MonoBehaviour,
            env.objects,
        )
    ]
    logger.info("MonoBehaviours: %d" % len(objs))
    candidates = [
        read_from_ptr(obj.m_GameObject, obj)
        for obj in filter(lambda obj: isinstance(obj, CubismModel), objs)
    ]
    crc_cache = dict()
    # fmt: off
    for OBJ in candidates:
        OBJ: GameObject
        components = [read_from_ptr(ptr, OBJ) for ptr in OBJ.m_Components]
        NAME = OBJ.m_Name
        MOC : CubismModel = next(filter(lambda x: isinstance(x, CubismModel), components), None)        
        PHY : CubismPhysicsController = next(filter(lambda x: isinstance(x, CubismPhysicsController), components), None)
        # ANI : Animator = next(filter(lambda x: isinstance(x, Animator), components), None)
        # RND : CubismRenderController = next(filter(lambda x: isinstance(x, CubismRenderController), components), None)
        logger.info(f"Processing {NAME}")
        outdir = os.path.join(args.outdir, NAME)
        os.makedirs(outdir, exist_ok=True)
        metadata = {
            "Version": 3,
            "FileReferences": {
                "Moc":"",
                "Textures": [],
                "Physics": ""
            },
        }
        if MOC:
            fname = metadata["FileReferences"]["Moc"] = f"{NAME}.moc3"
            with open(os.path.join(outdir, fname), "wb") as f:
                moc = read_from_ptr(MOC._moc, MOC.object_reader)
                moc = bytes(moc._bytes)
                logger.info(".moc3: %d bytes" % f.write(moc))
                try:
                    parts, parameters = read_moc3(io.BytesIO(moc))
                    for s in parts:
                        path = "Parts/" + s
                        crc_cache[crc32(path.encode("utf-8"))] = path
                    for s in parameters:
                        path = "Parameters/" + s
                        crc_cache[crc32(path.encode("utf-8"))] = path
                    logger.info(".moc3: %d parts, %d parameters" % (len(parts), len(parameters)))
                except Exception as e:
                    logger.warning("Failed to parse MOC3: %s" % e)
                    logger.warning("This may indicate obfuscation or a different format")
        if PHY:
            fname = metadata["FileReferences"]["Physics"] = f"{NAME}.physics3.json"
            with open(os.path.join(outdir, fname), "w") as f:
                logger.info(".physics3.json: %d bytes" % f.write(json.dumps(PHY.dump(),indent=4)))
        # Renderers are bound to the meshes in the hierarchy
        def children_recursive(obj: GameObject):
            transform : Transform = obj.m_Transform.read()
            for child in transform.m_Children:
                child = read_from_ptr(child, obj)
                ch_obj = child.m_GameObject.read()
                yield ch_obj
                yield from children_recursive(ch_obj)
        # Mark referenced textures
        TEX = set()
        for child in children_recursive(OBJ):
            components = [read_from_ptr(ptr, child) for ptr in child.m_Components]
            RND : CubismRenderer = next(filter(lambda x: isinstance(x, CubismRenderer), components), None)
            if RND:
                TEX.add(RND)
        if TEX:
            metadata["FileReferences"]["Textures"] = []
            for tex in TEX:
                tex : CubismRenderer
                tex : Texture2D = read_from_ptr(tex._mainTexture, tex)                
                path = f"Textures/{tex.m_Name}.png"
                metadata["FileReferences"]["Textures"].append(path)                
                path = os.path.join(outdir, path)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                tex.image.save(path)
                logger.info(f"[texture]: {tex.m_Name}")
            # XXX: Lexical. But why?
            metadata["FileReferences"]["Textures"].sort()
        path = f"{NAME}.model3.json"
        json.dump(metadata, open(os.path.join(outdir,path), "w"), indent=4)
        logger.info(f"[metadata]: {path}")
    # fmt: on
    if not args.no_anim:
        for reader in filter(
            lambda reader: reader.type == ClassIDType.AnimationClip, env.objects
        ):
            clip = reader.read()
            helper = AnimationHelper.from_clip(clip)
            motion3 = to_motion3(helper, crc_cache, clip)
            path = f"Animation/{clip.m_Name}.motion3.json"
            logger.info(f"[motion3]: {path}")
            path = os.path.join(args.outdir, path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            json.dump(motion3, open(path, "w"), indent=4)


if __name__ == "__main__":
    __main__()
