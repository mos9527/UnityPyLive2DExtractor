# Auto-generated by UnityPyLive2DExtractor/typetree_codegen.py
# Python definition for Live2D.Cubism.Framework.LookAt

from ..... import *

@typetree_defined
class CubismLookAxis(MonoBehaviour):
	value__ : int
@typetree_defined
class CubismLookController(MonoBehaviour):
	BlendMode : int
	_target : PPtr[Object]
	Center : PPtr[Transform]
	Damping : float
@typetree_defined
class CubismLookParameter(MonoBehaviour):
	Axis : int
	Factor : float
@typetree_defined
class CubismLookTargetBehaviour(MonoBehaviour):
	pass
@typetree_defined
class ICubismLookTarget(MonoBehaviour):
	pass
