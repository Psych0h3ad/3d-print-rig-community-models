"""Preserve native CAD surfaces and export connected, consistently shaded meshes."""
import re
import numpy as np
import trimesh
from scipy.spatial import cKDTree

def small_hardware(name,role):
 return role in ['metal','brass','native'] and bool(re.search(r'screw|washer|nut\b|bearing|pulley|heatset|heat.set|heat insert|gear|lead.?screw|threaded|^m[234568]\b',name,re.I))

def clean_mesh(mesh,reduce=False):
 mesh.merge_vertices(digits_vertex=8)
 mesh.update_faces(mesh.nondegenerate_faces(height=1e-10))
 mesh.update_faces(mesh.unique_faces())
 mesh.remove_unreferenced_vertices()
 count=len(mesh.faces)
 if reduce and count>5000:
  candidate=mesh.simplify_quadric_decimation(face_count=max(1500,int(count*.35)),aggression=3)
  candidate.update_faces(candidate.nondegenerate_faces(height=1e-10))
  candidate.remove_unreferenced_vertices()
  boundary=lambda m:int((np.bincount(m.edges_unique_inverse)!=2).sum())
  if candidate.is_winding_consistent and (not mesh.is_watertight or candidate.is_watertight) and boundary(candidate)<=boundary(mesh) and np.max(np.abs(candidate.bounds-mesh.bounds))<.00002:
   mesh=candidate
 shaded=trimesh.graph.smooth_shade(mesh,angle=np.deg2rad(30),facet_minarea=None)
 shaded.metadata.pop('original_components',None)
 normals=shaded.vertex_normals.copy()
 lengths=np.linalg.norm(normals,axis=1)
 valid=lengths>1e-10
 # Microscopic CAD faces can have zero normals at the display tolerance.
 # Use the nearest valid surface normal without changing any geometry.
 assert valid.any()
 if not valid.all():
  _,nearest=cKDTree(shaded.vertices[valid]).query(shaded.vertices[~valid])
  normals[~valid]=normals[valid][nearest]
 normals/=np.linalg.norm(normals,axis=1)[:,None]
 shaded._cache['vertex_normals']=normals
 assert shaded.is_winding_consistent
 assert np.isfinite(shaded.vertices).all() and np.isfinite(shaded.vertex_normals).all()
 return shaded
