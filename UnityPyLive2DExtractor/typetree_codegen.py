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

from collections import defaultdict
import argparse, json


def translate_name(m_Name: str, **kwargs):
    m_Name = m_Name.replace("<>", "__generic_")  # Generic templates
    m_Name = m_Name.replace("<", "_").replace(">", "_")  # Templated
    return m_Name


from UnityPy import classes


def translate_type(
    m_Type: str, strip=False, fallback=True, typenames: dict = dict(), **kwargs
):
    if m_Type in BASE_TYPE_MAP:
        return BASE_TYPE_MAP[m_Type]
    if getattr(classes, m_Type, None):
        return m_Type
    if m_Type in typenames:
        return m_Type
    if m_Type.endswith("[]"):
        m_Type = translate_type(m_Type[:-2], strip, fallback, typenames)
        if not strip:
            return f"List[{m_Type}]"
        else:
            return m_Type
    if m_Type.startswith("PPtr<"):
        m_Type = translate_type(m_Type[5:-1], strip, fallback, typenames)
        if not strip:
            return f"PPtr[{m_Type}]"
        else:
            return m_Type
    if fallback:
        return "object"
    else:
        return m_Type


def declare_field(name: str, type: str):
    if name.startswith("_"):
        # attrs treat these as private. Alias them
        # https://www.attrs.org/en/stable/init.html#private-attributes-and-aliases
        return f"{name} : {type} = attrs_field(alias='{name}', init=True)"
    else:
        return f"{name} : {type}"


def __main__():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "infile",
        type=str,
        help="Input file. Dump with https://github.com/K0lb3/TypeTreeGenerator",
    )
    parser.add_argument("outfile", type=str, help="Output file")
    args = parser.parse_args()
    TYPETREE_DEFS = json.load(open(args.infile, "r"))
    TYPETREE_DEFS_BY_NAME = {k.split(".")[-1]: v for k, v in TYPETREE_DEFS.items()}
    # Sort the keys in topological order
    # We don't assume the guarantee otherwise
    graph = {
        clazz: {
            translate_type(field["m_Type"], strip=True, fallback=False)
            for field in fields
            # Don't care about built-ins
        }
        for clazz, fields in TYPETREE_DEFS_BY_NAME.items()
    }
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

    for clazz in graph:
        if not vis[clazz]:
            dfs(clazz)

    f = open(args.outfile, "w", encoding="utf-8")

    def emit_line(*lines: str):
        for line in lines:
            f.write(line)
            f.write("\n")
        if not lines:
            f.write("\n")

    # fmt: off
    emit_line(
        "# fmt: off",
        "# Auto-generated by https://github.com/mos9527/UnityPyLive2DExtractor/tree/main/UnityPyLive2DExtractor/typetree_codegen.py",
        ""
        "from typing import List, Union, Optional, TypeVar", 
        "from UnityPy.classes import *",
        "from UnityPy.classes.math import (ColorRGBA, Matrix3x4f, Matrix4x4f, Quaternionf, Vector2f, Vector3f, Vector4f, float3, float4,)",
        "from attrs import field as attrs_field, define as attrs_define",        
        """def unitypy_define_ex(cls):
    # Allows deep inheritance and private fields. See `declare_field` in the codegen
    cls = attrs_define(cls, slots=True, kw_only=True)
    return cls
"""
        "TYPETREE_DEFS = " + json.dumps(TYPETREE_DEFS, indent=4),
    )    
    # fmt: on
    # Emit by topo order
    clazzes = list()
    dp = defaultdict(lambda: -1)
    for clazz in topo:
        fields = TYPETREE_DEFS_BY_NAME.get(clazz, None)
        if not fields:
            print("* skipping", clazz, " - does not exisit in TypeTree definition")
            continue
        # Heuristic: If there is a lvl1 field, it's a subclass
        lvl1 = list(filter(lambda field: field["m_Level"] == 1, fields))
        emit_line("@unitypy_define_ex")
        clazz = translate_name(clazz)
        clazzes.append(clazz)
        num_fields = 0
        if lvl1:
            parent = translate_type(fields[0]["m_Type"], strip=True, fallback=False)
            emit_line(f"class {clazz}({parent}):")
            # Generated typedefs are guaranteed to be flat in hierarchy
            # Recursive ones are defined by previous/topo order
            if dp[parent] == -1:
                # Reuse parent's fields with best possible effort
                # This is a heuristic and may not be correct
                if pa_dep1 := getattr(classes, parent, None):
                    dp[parent] = len(pa_dep1.__attrs_attrs__)
                else:
                    raise RecursionError("Circular inheritance detected")
            pa_dep1 = dp[parent]
            cur_dep1 = 0
            for i, field in enumerate(
                filter(lambda field: field["m_Level"] == 1, fields)
            ):
                if i < pa_dep1:
                    # Skip parent fields at lvl1
                    continue
                emit_line(
                    f"\t{declare_field(field['m_Name'],translate_type(**field, typenames=TYPETREE_DEFS_BY_NAME))}"
                )
                cur_dep1 += 1
                num_fields += 1
            dp[clazz] = cur_dep1
        else:
            # No inheritance
            emit_line(f"class {clazz}")
            for field in fields:
                emit_line(
                    f"\t{declare_field(field['m_Name'],translate_type(**field, typenames=TYPETREE_DEFS_BY_NAME))}"
                )
                num_fields += 1
        if not num_fields:
            emit_line("\tpass", "")
        else:
            emit_line()
    emit_line("__classes__ = [" + ",".join(clazzes) + "]")
    emit_line("# fmt: on")
    f.close()


if __name__ == "__main__":
    __main__()
