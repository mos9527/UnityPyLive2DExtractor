"""Simple codegen for typetree classes

- Supports nested types
- Supports inheritance
- Automatically resolves import order and dependencies
- Generated classes support nested types, and will be initialized with the correct types even with nested dicts

NOTE:
- Cannot resolve namespace conflicts if the same class name is defined in multiple namespaces
- Missing type definitions are marked with # XXX: Fallback of {org_type} and typedefed as object
- Circular inheritance is checked and raises RecursionError
- The output order (imports, classes) are deterministic and lexicographically sorted
- The output is emitted in lieu of the Namespace structure of the TypeTree dump, presented as Python modules in directories

USAGE:

    python typetree_codegen.py <typetree_dump.json> <output_dir>
"""

# From https://github.com/K0lb3/UnityPy/blob/master/generators/ClassesGenerator.py
BASE_TYPE_MAP = {
    "char": "str",
    "short": "int",
    "int": "int",
    "long long": "int",
    "unsigned short": "int",
    "unsigned int": "int",
    "unsigned long long": "int",
    "UInt8": "int",
    "UInt16": "int",
    "UInt32": "int",
    "UInt64": "int",
    "SInt8": "int",
    "SInt16": "int",
    "SInt32": "int",
    "SInt64": "int",
    "Type*": "int",
    "FileSize": "int",
    "float": "float",
    "double": "float",
    "bool": "bool",
    "string": "str",
    "TypelessData": "bytes",
    # -- Extra
    "Byte[]": "bytes",
    "Byte": "int",
    "String": "str",
    "Int32": "int",
    "Single": "float",
    "Color": "ColorRGBA",
    "Vector2": "Vector2f",
    "Vector3": "Vector3f",
    "Vector4": "Vector4f",
}
# XXX: Can't use attrs here since subclassing MonoBehavior and such - though defined by the typetree dump
# seem to be only valid if the class isn't a property of another class
# In which case the MonoBehavior attributes are inherited by the parent class and does not
# initialize the property class
# XXX: Need some boilerplate to handle this
HEADER = "\n".join(
    [
        "# fmt: off",
        "# Auto-generated by https://github.com/mos9527/UnityPyLive2DExtractor/tree/main/UnityPyLive2DExtractor/typetree_codegen.py",
        "" "from typing import List, Union, Optional, TypeVar",
        "from UnityPy.classes import *",
        "from UnityPy.classes.math import (ColorRGBA, Matrix3x4f, Matrix4x4f, Quaternionf, Vector2f, Vector3f, Vector4f, float3, float4,)",
        '''T = TypeVar("T")
def typetree_defined(clazz : T) -> T:
	"""dataclass-like decorator for typetree classess with nested type support
	
	limitations:
	- the behavior is similar to slotted dataclasses where shared attributes are inherited
	  but allows ommiting init of the parent if kwargs are not sufficient
	- generally supports nested types, however untested and could be slow	
    - and ofc, zero type checking and safeguards :/	
	"""
	RESERVED_KWS = {'object_reader'}
    # Allow these to be propogated to the props
	def __init__(self, **d):
		def enusre_reserved(obj):
			for k in RESERVED_KWS:
				if hasattr(obj, k) and k in d:
					setattr(obj, k, d[k])
			return obj		
		def reduce_init(clazz, **d):
			types : dict = clazz.__annotations__
			for k, sub in types.items():
				if type(sub) == str:
					sub = eval(sub) # attrs turns these into strings...why?
				reduce_arg = getattr(sub, "__args__", [None])[0]
				if isinstance(d[k], list):
					if hasattr(reduce_arg, "__annotations__") or hasattr(reduce_arg, "__args__"):
						setattr(self, k, [enusre_reserved(reduce_arg(**x)) for x in d[k]])
					else:
						setattr(self, k, [enusre_reserved(reduce_arg(x)) for x in d[k]])
				elif isinstance(d[k], dict) and hasattr(sub, "__annotations__"):
					setattr(self, k, enusre_reserved(sub(**d[k])))
				else:
					if isinstance(d[k], dict):
						setattr(self, k, enusre_reserved(sub(**d[k])))
					else:
						setattr(self, k, enusre_reserved(sub(d[k])))			
		for __base__ in clazz.__bases__:
			types : dict = __base__.__annotations__
			args = {k:d[k] for k in types if k in d}
			if len(args) == len(types):
				super(clazz, self).__init__(**args)
				reduce_init(__base__, **d)
				for k in args:
					if not k in RESERVED_KWS: del d[k]
		reduce_init(clazz, **d)
		enusre_reserved(self)
	def __repr__(self) -> str:
		return f"{clazz.__name__}({', '.join([f'{k}={getattr(self, k)!r}' for k in self.__annotations__])})"
	clazz.__init__ = __init__
	clazz.__repr__ = __repr__
	return clazz
''',
    ]
)
from collections import defaultdict
from dataclasses import dataclass
import argparse, json


@dataclass
class CodegenFlags:
    pass


FLAGS = CodegenFlags()


def translate_name(m_Name: str, **kwargs):
    m_Name = m_Name.replace("<>", "__generic_")  # Generic templates
    m_Name = m_Name.replace("<", "_").replace(">", "_")  # Templated
    m_Name = m_Name.replace("=", "_")  # Special chars
    return m_Name


from UnityPy import classes
from logging import getLogger
from coloredlogs import install

logger = getLogger("codegen")


def translate_type(
    m_Type: str,
    strip=False,
    fallback=True,
    typenames: dict = dict(),
    parent: str = "",
    **kwargs,
):
    if m_Type in BASE_TYPE_MAP:
        return BASE_TYPE_MAP[m_Type]
    if getattr(classes, m_Type, None):
        return m_Type
    if m_Type in typenames:
        if m_Type == parent:
            return f'"{m_Type}"'
        else:
            return m_Type
    if m_Type.endswith("[]"):
        m_Type = translate_type(m_Type[:-2], strip, fallback, typenames, parent)
        if not strip:
            return f"List[{m_Type}]"
        else:
            return m_Type
    if m_Type.startswith("PPtr<"):
        m_Type = translate_type(m_Type[5:-1], strip, fallback, typenames, parent)
        if not strip:
            return f"PPtr[{m_Type}]"
        else:
            return m_Type
    if fallback:
        logger.warning(f"Unknown type {m_Type}, using fallback")
        return "object"
    else:
        if m_Type == parent:
            return f'"{m_Type}"'
        else:
            return m_Type


def declare_field(name: str, type: str, org_type: str = None):
    if type not in {"object", "List[object]", "PPtr[object]"}:
        return f"{name} : {type}"
    else:
        return f"{name} : {type} # XXX: Fallback of {org_type}"


from io import TextIOWrapper


def topsort(graph: dict):
    # Sort the keys in topological order
    # We don't assume the guarantee otherwise
    graph = {k: list(sorted(v)) for k, v in graph.items()}
    vis = defaultdict(lambda: 0)
    topo = list()

    def dfs(u):
        vis[u] = 1
        for v in graph.get(u, []):
            if vis[v] == 1:
                return False
            if vis[v] == 0 and not dfs(v):
                return False
        vis[u] = 2
        topo.append(u)
        return True

    flag = 1
    for clazz in graph:
        if not vis[clazz]:
            flag &= dfs(clazz)
    assert flag, "circular dependency detected. bogus typetree dump"
    return topo


def process_namespace(
    namespace: str,
    typetree_defs: dict,
    f: TextIOWrapper,
    import_root: str = "",
    import_defs: dict = dict(),
):
    def emit_line(*lines: str):
        for line in lines:
            f.write(line)
            f.write("\n")
        if not lines:
            f.write("\n")

    namespace = namespace or "<default namespace>"
    logger.info(f"Subpass 1: Generating class dependency graph for {namespace}")
    emit_line("# Auto-generated by UnityPyLive2DExtractor/typetree_codegen.py")
    emit_line(f"# Python definition for {namespace}", "")
    if import_root:
        emit_line(f"from {import_root} import *")
    for clazz, parent in import_defs.items():
        emit_line(f"from {import_root or '.'}{parent or ''} import {clazz}")

    emit_line()
    # Emit by topo order
    graph = {
        clazz: {
            translate_type(field["m_Type"], strip=True, fallback=False)
            for field in fields
            # Don't care about built-ins
        }
        for clazz, fields in typetree_defs.items()
    }
    for u, vs in graph.items():
        # This is circular - but allowed
        # We can have a class that references itself
        if u in vs:
            vs.remove(u)
    topo = topsort(graph)
    clazzes = list()

    logger.info(f"Subpass 2: Generating code for {namespace}")
    dp = defaultdict(lambda: -1)
    for clazz in topo:
        fields = typetree_defs.get(clazz, None)
        if not fields:
            logger.debug(
                f"Class {clazz} has no fields defined in TypeTree dump, skipped"
            )
            continue

        def deduce_type(i: int):
            # XXX: Upstream needs to fix this
            if fields[i]["m_Type"].endswith("[]"):
                assert fields[i + 1]["m_Type"] == "Array"
                return fields[i + 3]["m_Type"] + "[]"
            else:
                return fields[i]["m_Type"]

        # Heuristic: If there is a lvl1 field, it's a subclass
        lvl1 = list(filter(lambda field: field["m_Level"] == 1, fields))
        clazz = translate_name(clazz)
        clazzes.append(clazz)
        clazz_fields = list()
        emit_line(f"@typetree_defined")
        if lvl1:
            parent = translate_type(fields[0]["m_Type"], strip=True, fallback=False)
            emit_line(f"class {clazz}({parent}):")
            # Generated typedefs are guaranteed to be flat in hierarchy
            # Recursive ones are defined by previous/topo order
            if dp[parent] == -1:
                # Reuse parent's fields with best possible effort
                # This is a heuristic and may not be correct
                if pa_dep1 := getattr(classes, parent, None):
                    dp[parent] = len(pa_dep1.__annotations__)
                else:
                    raise RecursionError("Circular inheritance detected")
            pa_dep1 = dp[parent]
            cur_dep1 = pa_dep1
            for nth, (i, field) in enumerate(
                filter(lambda x: x[1]["m_Level"] == 1, enumerate(fields))
            ):
                if nth < pa_dep1:
                    # Skip parent fields at lvl1
                    continue
                raw_type = deduce_type(i)
                name, type = field["m_Name"], translate_type(
                    raw_type, typenames=typetree_defs | import_defs, parent=clazz
                )
                emit_line(f"\t{declare_field(name, type, raw_type)}")
                clazz_fields.append((name, type, raw_type))
                cur_dep1 += 1
            dp[clazz] = cur_dep1
        else:
            # No inheritance
            emit_line(f"class {clazz}:")
            for i, field in enumerate(fields):
                raw_type = deduce_type(i)
                name, type = field["m_Name"], translate_type(
                    raw_type, typenames=typetree_defs | import_defs, parent=clazz
                )
                emit_line(f"\t{declare_field(name, type, raw_type)}")
                clazz_fields.append((name, type))
        if not clazz_fields:
            # Empty class. Consider MRO
            emit_line("\tpass")


import os, shutil
from typing import Dict


def __main__():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "infile",
        type=str,
        help="Input TypeTree Dump in JSON format. Dump with https://github.com/K0lb3/TypeTreeGenerator",
    )
    parser.add_argument("outdir", type=str, help="Output directory")
    parser.add_argument("--log-level", default="INFO", help="Set logging level")
    args = parser.parse_args()
    install(level=args.log_level)

    shutil.rmtree(args.outdir, ignore_errors=True)
    logger.info(f"Reading from {args.infile}")
    TYPETREE_DEFS = json.load(open(args.infile, "r"))
    namespaces = defaultdict(dict)
    namespacesT = defaultdict(None)
    logger.info("Pass 1: Building namespace")
    for key in TYPETREE_DEFS:
        fullkey = key.split(".")
        if len(fullkey) == 1:
            namespace, clazz = None, fullkey[0]
        else:
            namespace, clazz = fullkey[:-1], fullkey[-1]
            namespace = ".".join(namespace)
        namespaces[namespace][clazz] = TYPETREE_DEFS[key]
        if clazz not in namespacesT:
            namespacesT[clazz] = namespace
        else:
            logger.error(
                f"Class {clazz} already defined in {namespacesT[clazz]} but found again in {namespace}"
            )
            logger.error(
                f"Need manual intervention to resolve the conflict. Using first definition for now."
            )
    logger.info("Pass 2: Generating import graph")
    # Build import graph
    namespaceDeps = defaultdict(set)
    for namespace, typetree_defs in namespaces.items():
        for clazz, fields in typetree_defs.items():
            for field in fields:
                type = translate_type(field["m_Type"], strip=True, fallback=False)
                if type in namespacesT and namespacesT[type] != namespace:
                    namespaceDeps[namespace].add(type)
    handles: Dict[str, TextIOWrapper] = dict()

    def __open(fname: str):
        fname = os.path.join(args.outdir, fname)
        if fname not in handles:
            os.makedirs(os.path.dirname(fname), exist_ok=True)
            handles[fname] = open(fname, "w")
        return handles[fname]

    logger.info("Pass 3: Emitting namespace as Python modules")
    __open("__init__.py").write(HEADER)
    # XXX: This part can be trivally parallelized
    for namespace, typetree_defs in sorted(
        namespaces.items(), key=lambda x: x[0].count(".") if x[0] else 0
    ):
        # CubismTaskHandler -> generated/__init__.py
        # Live2D.Cubism.Core.CubismMoc -> generated/Live2D/Cubism/Core/__init__.py
        deps = {k: namespacesT[k] for k in namespaceDeps[namespace]}
        deps = dict(sorted(deps.items()))
        if namespace:
            ndots = namespace.count(".") + 2
            dotss = "." * ndots
            f = __open(os.path.join(*namespace.split("."), "__init__.py"))
            process_namespace(namespace, typetree_defs, f, dotss, deps)
        else:
            f = __open("__init__.py")
            process_namespace(namespace, typetree_defs, f, import_defs=deps)
    __open("__init__.py").write(
        "\nTYPETREE_DEFS = " + json.dumps(TYPETREE_DEFS, indent=4)
    )
    logger.info("All done. Going home.")


if __name__ == "__main__":
    __main__()
