"""Rebuild a pinned display assembly from its prepared native BREP leaves."""
from pathlib import Path
import argparse,gzip,hashlib,io,json
import cadquery as cq
import numpy as np
import trimesh
from OCP.BRepTools import BRepTools
from native_mesh import clean_mesh,small_hardware

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--cache',type=Path,required=True)
 p.add_argument('--model',type=Path,required=True)
 p.add_argument('--coarse-hardware',action='store_true',help='Use 0.3 mm / 0.8 rad hardware tessellation, as in the VzBot display.')
 a=p.parse_args();folder=a.model
 manifest=json.loads((folder/'assembly_manifest.json').read_text(encoding='utf8'))
 profile=json.loads((folder/'machine_profile.json').read_text(encoding='utf8'))
 original=trimesh.load(io.BytesIO(gzip.decompress((folder/'model.glb.gz').read_bytes())),file_type='glb',process=False)
 scene=trimesh.Scene();triangles=0
 for part in manifest['parts']:
  key=part['key'];old=original.geometry['part_'+key]
  shape=cq.Shape.importBrep(str(a.cache/(key+'.brep')));BRepTools.Clean_s(shape.wrapped)
  hardware=small_hardware(part['name'],part['appearance_role'])
  vertices,faces=shape.tessellate(.3,.8)if hardware and a.coarse_hardware else shape.tessellate(.2,.3)
  coords=(np.array([v.toTuple()for v in vertices])+part.get('native_adjustment_mm',[0,0,0])-np.array(profile['origin_mm']))@np.array(profile['basis']).T*.001
  mesh=clean_mesh(trimesh.Trimesh(vertices=coords,faces=faces,process=False),hardware)
  mesh.visual=old.visual.copy();mesh.metadata=old.metadata.copy()
  scene.add_geometry(mesh,geom_name='part_'+key,node_name='part_'+key);triangles+=len(mesh.faces)
 raw=scene.export(file_type='glb',include_normals=True)
 (folder/'model.glb.gz').write_bytes(gzip.compress(raw,9,mtime=0))
 manifest['triangles']=triangles
 (folder/'assembly_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
 index=json.loads((folder/'INDEX.json').read_text(encoding='utf8'))
 for name,spec in index['files'].items():
  data=(folder/Path(spec['path']).name).read_bytes();spec.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
  if name=='model.glb':spec.update(decoded_bytes=len(raw),decoded_sha256=hashlib.sha256(raw).hexdigest())
 (folder/'INDEX.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf8')
 print(f"Rebuilt {manifest['native_leaf_count']} leaves and {triangles} triangles.")

if __name__=='__main__':main()
