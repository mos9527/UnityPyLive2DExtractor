import argparse
import os
import json
import pathlib
import UnityPy
import io
from zlib import crc32
from typing import List
from sssekai.fmt import moc3,motion3
from UnityPy.enums import ClassIDType
from UnityPy.classes import MonoBehaviour, Texture2D, PPtr
from UnityPy.math import Vector2, Vector4
from UnityPy.streams import EndianBinaryReader
from logging import getLogger
import coloredlogs
from . import __version__
logger = getLogger('UnityPyLive2DExtractor')
class CubismRenderer(MonoBehaviour):
    LocalSortingOrder: int
    Color : Vector4
    MainTexture : PPtr
    SortingMode : int
    SortingOrder : int
    RenderOrder : int
    DepthOffset : float
    Opacity : float
    def __init__(self, reader: EndianBinaryReader):
        super().__init__(reader)
        self.LocalSortingOrder = reader.read_int()
        self.Color = reader.read_vector4()
        self.MainTexture = PPtr(reader)
        self.SortingMode = reader.read_int()
        self.SortingOrder = reader.read_int()
        self.RenderOrder = reader.read_int()
        self.DepthOffset = reader.read_float()
        self.Opacity = reader.read_float()
    def __hash__(self):
        return self.MainTexture.path_id
    def __eq__(self, other):
        return type(other) == type(self) and hash(self) == hash(other)
class CubismMoc(MonoBehaviour):
    Binary: bytes
    def __init__(self, reader: EndianBinaryReader):
        super().__init__(reader)
        self.Binary = reader.read_byte_array() 
class CubismPhysicsNormalizationTuplet:
    Maximum : float
    Minimum : float
    Default : float
    def __init__(self, reader: EndianBinaryReader):
        self.Maximum = reader.read_float()
        self.Minimum = reader.read_float()
        self.Default = reader.read_float()
    def dump(self):
        return {
            'Maximum': self.Maximum,
            'Minimum': self.Minimum,
            'Default': self.Default
        }
class CubismPhysicsNormalization:
    Position : CubismPhysicsNormalizationTuplet
    Angle : CubismPhysicsNormalizationTuplet
    def __init__(self, reader: EndianBinaryReader):
        self.Position = CubismPhysicsNormalizationTuplet(reader)
        self.Angle = CubismPhysicsNormalizationTuplet(reader)
    def dump(self):
        return {
            'Position':self.Position.dump(),
            'Angle':self.Angle.dump()
        }
class CubismPhysicsParticle:
    InitialPosition : Vector2
    Mobility : float
    Delay : float
    Acceleration : float
    Radius : float
    def __init__(self, reader: EndianBinaryReader):
        self.InitialPosition = reader.read_vector2()
        self.Mobility = reader.read_float()
        self.Delay = reader.read_float()
        self.Acceleration = reader.read_float()
        self.Radius = reader.read_float()
    def dump(self):
        return {
            'Position': {'X':self.InitialPosition.X,'Y':self.InitialPosition.Y},
            'Mobility':self.Mobility,
            'Delay':self.Delay,
            'Acceleration':self.Acceleration,
            'Radius':self.Radius
        }
class CubismPhysicsOutput:
    DestinationId: str
    ParticleIndex: int
    TranslationScale: Vector2
    AngleScale: float
    Weight: float
    SourceComponent: int
    IsInverted: bool
    def __init__(self, reader: EndianBinaryReader):
        self.DestinationId = reader.read_aligned_string()
        self.ParticleIndex = reader.read_int()
        self.TranslationScale = reader.read_vector2()
        self.AngleScale = reader.read_float()
        self.Weight = reader.read_float()
        self.SourceComponent = reader.read_int()
        self.IsInverted = reader.read_boolean()
        reader.align_stream()
    def dump(self):
        return {
            'Destination':{'Target':'Parameter', 'Id':self.DestinationId},
            'VertexIndex':self.ParticleIndex,
            'Scale':self.AngleScale,
            'Weight':self.Weight,
            'Type':['X','Y','Angle'][self.SourceComponent],
            'Reflect':self.IsInverted
        }        
class CubismPhysicsInput:
    SourceId: str
    ScaleOfTranslation: Vector2
    AngleScale: float
    Weight: float
    SourceComponent: int
    IsInverted: bool
    def __init__(self, reader: EndianBinaryReader):
        self.SourceId = reader.read_aligned_string()
        self.ScaleOfTranslation = reader.read_vector2()
        self.AngleScale = reader.read_float()
        self.Weight = reader.read_float()
        self.SourceComponent = reader.read_int()
        self.IsInverted = reader.read_boolean()
        reader.align_stream()
    def dump(self):
        return {
            'Source':{'Target':'Parameter', 'Id':self.SourceId},
            'Weight':self.Weight,
            'Type':['X','Y','Angle'][self.SourceComponent],
            'Reflect':self.IsInverted
        }
class CubismPhysicsSubRig:
    Input: List[CubismPhysicsInput]
    Output: List[CubismPhysicsOutput]
    Particles: List[CubismPhysicsParticle]
    Normalization: CubismPhysicsNormalization
    def __init__(self, reader: EndianBinaryReader):
        num_input = reader.read_int()
        self.Input = [CubismPhysicsInput(reader) for _ in range(num_input)]        
        num_output = reader.read_int()
        self.Output = [CubismPhysicsOutput(reader) for _ in range(num_output)]        
        num_particles = reader.read_int()
        self.Particles = [CubismPhysicsParticle(reader) for _ in range(num_particles)]        
        self.Normalization = CubismPhysicsNormalization(reader) 
    def dump(self):
        return {
            'Input':[x.dump() for x in self.Input],
            'Output':[x.dump() for x in self.Output],
            'Vertices':[x.dump() for x in self.Particles],
            'Normalization':self.Normalization.dump()
        }
class CubismPhysicsRig:
    SubRigs: List[CubismPhysicsSubRig]
    def __init__(self, reader: EndianBinaryReader):
        num_sub_rigs = reader.read_int()
        self.SubRigs = [CubismPhysicsSubRig(reader) for _ in range(num_sub_rigs)]
    def dump(self):
        return [{"Id": "PhysicsSetting%d" % (i + 1), **rig.dump()} for i, rig in enumerate(self.SubRigs)]
class CubismPhysicsController(MonoBehaviour):
    Rig: CubismPhysicsRig
    def __init__(self, reader: EndianBinaryReader):
        super().__init__(reader)
        self.Rig = CubismPhysicsRig(reader)
    def dump(self):
        return {
            "Version": 3,
            "Meta": {
                "PhysicsSettingCount": len(self.Rig.SubRigs),
                "TotalInputCount": sum((len(x.Input) for x in self.Rig.SubRigs)),
                "TotalOutputCount": sum((len(x.Output) for x in self.Rig.SubRigs)),
                "VertexCount": sum((len(x.Particles) for x in self.Rig.SubRigs)),
                "Fps": 60,
                "EffectiveForces": {"Gravity": {"X": 0,"Y": -1},"Wind": {"X": 0,"Y": 0}},
                "PhysicsDictionary":[{"Id":"PhysicsSetting%d"%(i+1), "Name":"%d"%(i+1)} for i, _ in enumerate(self.Rig.SubRigs)]
            },
            'PhysicsSettings': self.Rig.dump()
        }
def __main__():
    parser = argparse.ArgumentParser(description='UnityPyLive2D Extractor v%d.%d.%d' % __version__)
    parser.add_argument('infile', help='Input file/directory to extract from')
    parser.add_argument('outdir', help='Output directory to extract to')
    parser.add_argument('--log-level', help='Set logging level', default='DEBUG', choices=['DEBUG','INFO','WARNING','ERROR','CRITICAL'])
    parser.add_argument('--no-anim', help='Do not extract animations', action='store_true')
    args = parser.parse_args()
    coloredlogs.install(
        level=args.log_level,
        fmt="%(asctime)s %(name)s [%(levelname).4s] %(message)s",
        isatty=True
    )
    os.makedirs(args.outdir, exist_ok=True)
    env = UnityPy.load(args.infile)
    # Helpers
    filter_className = lambda obj, className: obj.type == ClassIDType.MonoBehaviour and obj.m_Script.get_obj().read().m_ClassName == className
    comp_get_parent = lambda objs: [obj.m_Transform.read().m_Father.read().m_GameObject.read() for obj in objs]
    # Comprehesions
    objs = [pobj.read() for pobj in env.objects if pobj.type in {ClassIDType.MonoBehaviour, ClassIDType.AnimationClip, ClassIDType.GameObject, ClassIDType.Texture2D}]
    logger.info('Preprocessing %d objects' % len(objs))
    anim = [obj for obj in objs if obj.type == ClassIDType.AnimationClip]
    logger.debug('Found %d animations' % len(anim))
    mocs = {obj.name : CubismMoc(obj.reader) for obj in objs if filter_className(obj, 'CubismMoc')}
    logger.debug('Found %d MOC Binaries' % len(mocs))
    phys = {obj.m_GameObject.read().name : CubismPhysicsController(obj.reader) for obj in objs if filter_className(obj, 'CubismPhysicsController')}
    logger.debug('Found %d Physics Controllers' % len(phys))
    rnd_obj = [CubismRenderer(obj.reader) for obj in objs if filter_className(obj, 'CubismRenderer')]
    # Parent GameObject/Drawable/CubismRenderer
    rnd_pa = comp_get_parent((tex.m_GameObject.read() for tex in rnd_obj))
    rnd_pa = comp_get_parent(rnd_pa)
    rnds = {tex.name : set() for tex in rnd_pa}
    # Filter unique Texture2D objects. See CubismRenderer for its hash function
    for tex, rnd_pa in zip(rnd_obj, rnd_pa): rnds[rnd_pa.name].add(tex)
    logger.debug('Found %d Unique Textures' % sum(len(x) for x in rnds.values()))
    CRC_HASH_TABLE = dict()
    for name, moc in mocs.items():
        logger.info('Processing %s' % name)
        moc : CubismMoc
        phy : CubismPhysicsController
        phy = phys.get(name,None)
        rnd = rnds.get(name,set())        
        model3 = {
            "Version": 3,
            "FileReferences": {
                "Moc": name + '.moc3',
                "Textures": [],
                "Physics": name + '.physics3.json'
            }
        }
        for r in rnd:
            r : CubismRenderer
            tex : Texture2D
            tex = r.MainTexture.read()
            relpath = os.path.join('textures', name, tex.name + '.png')
            fpath = os.path.join(args.outdir, relpath)
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath,'wb') as f:
               tex.image.save(f, format='png') or logger.debug('... Texture saved: %s' % fpath)
            model3['FileReferences']['Textures'].append(pathlib.Path(relpath).as_posix())
        # XXX: We don't know where to find the exact order of the textures (yet) so we sort them in ascending lexicographical order
        # since would probably be the case anyways
        model3['FileReferences']['Textures'] = sorted(model3['FileReferences']['Textures'])
        with open(os.path.join(args.outdir, name + '.moc3'),'wb') as f:
            f.write(moc.Binary) and logger.debug('... Mesh saved: %s' % f.name)
            if not args.no_anim:                
                parts, parameters = moc3.read_moc3(io.BytesIO(moc.Binary))
                for s in parts:
                    path = 'Parts/' + s
                    CRC_HASH_TABLE[crc32(path.encode('utf-8'))] = path
                for s in parameters:
                    path = 'Parameters/' + s
                    CRC_HASH_TABLE[crc32(path.encode('utf-8'))] = path                    
        if phy:
            with open(os.path.join(args.outdir, name + '.physics3.json'),'w', encoding='utf-8') as f:
                json.dump(phy.dump(),f, indent=4, ensure_ascii=False) or logger.debug('... Physics saved: %s' % f.name)
        with open(os.path.join(args.outdir, name + '.model3.json'),'w', encoding='utf-8') as f:
            json.dump(model3,f, indent=4, ensure_ascii=False) or logger.debug('... Model saved: %s' % f.name)
    if not args.no_anim:
        os.makedirs(os.path.join(args.outdir, 'animations'), exist_ok=True)
        for a in anim:
            logger.info('Parsing animation %s' % a.name)
            with open(os.path.join(args.outdir, 'animations', a.name + '.motion3.json'),'w', encoding='utf-8') as f:
                json.dump(motion3.unity_animation_clip_to_motion3(a, CRC_HASH_TABLE),f, indent=4, ensure_ascii=False) or logger.debug('... Animation saved: %s' % f.name)

if __name__ == '__main__':
    __main__()