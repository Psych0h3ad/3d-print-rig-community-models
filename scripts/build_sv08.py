from pathlib import Path
import sys,json,re,gzip,hashlib
import numpy as np,cadquery as cq,trimesh
from trimesh.visual.material import PBRMaterial

import argparse
args=argparse.ArgumentParser();args.add_argument('--cache',type=Path,required=True);args.add_argument('--output',type=Path,required=True);a=args.parse_args()
R=Path(__file__).resolve().parents[1];D=a.cache;O=a.output
O.mkdir(parents=True,exist_ok=True)
rows=json.loads((D/'inventory.json').read_text(encoding='utf8'))
placements=json.loads((R/'scripts/SV08_PLACEMENTS.json').read_text(encoding='utf8'))
reference=set(placements.get('reference_leaves',[]))
colors={'base':[36,39,44,255],'accent':[62,103,171,255],'frame':[35,38,42,255],'motor':[33,36,39,255],'metal':[176,181,187,255],'brass':[186,144,59,255],'rubber':[24,27,30,255],'tube':[226,229,231,255],'board':[36,83,55,255],'bed_surface':[55,58,62,255]}

def role(r):
    n=r['name'].lower();k=r['key']
    if k in ['581','694']:return 'accent'
    if k in ['670','671']:return 'bed_surface'
    if k in ['91','165','233','298','90','166','232','301','625']:return 'rubber'
    if k in ['578','626']:return 'tube'
    if k=='709':return 'metal'
    if any(w in n for w in ['pcb','board','sensor assembly']):return 'board'
    if ('motor'in n and not any(w in n for w in ['mount','knob','wheel'])) or ('fan'in n and not any(w in n for w in ['bracket','mount','deflector'])):return 'motor'
    if re.search(r'JXHSV\w+-\d+-d',r['name'],re.I):return 'base'
    if any(w in n for w in ['spring','screw','spcer','spacer','shaft','bearing','rail','slider','sliding block','synchronous wheel','idler','gear','fastener','heating block','magnet','latch']):return 'metal'
    if any(w in n for w in ['silicone','belt','seal','pressure sensor']):return 'rubber'
    if 'profile'in n:return 'frame'
    return 'native'

scene=trimesh.Scene();parts=[];triangles=0
for r in rows:
    key=r['key'];s=cq.Shape.importBrep(str(D/(key+'.brep')))
    shift=placements.get('translations',{}).get(key,[0,0,0]);v,f=s.tessellate(.20,.30)
    assert f,('Empty native part',key)
    verts=np.array([p.toTuple()for p in v])
    if key in ['578','625'] and placements.get('flex_adjustment_mm'):
        head,fixed=({'578':([-86.579,137.755,242.440],[-90.021,315.509,-29.268]),'625':([-99.579,147.967,242.220],[-221.414,330.722,-.665])})[key]
        # Keep both native fitting collars rigid; blend only the supplied
        # tube/wire body for the raised static display pose.
        dh=np.maximum(0,np.linalg.norm(verts-head,axis=1)-35)
        df=np.maximum(0,np.linalg.norm(verts-fixed,axis=1)-8)
        u=df/np.maximum(1e-9,dh+df);weight=u*u*(3-2*u)
        verts[:,1]+=placements['flex_adjustment_mm']*weight
    verts=(verts+shift-np.array([-67.965, -62.653, 153.7417]))*.001
    m=trimesh.Trimesh(vertices=verts,faces=f,process=False)
    # Remove only zero-area display triangles, never supports or hardware.
    m.update_faces(m.nondegenerate_faces(height=1e-10));m.remove_unreferenced_vertices()
    role_name=role(r)
    assert len(m.faces) and np.isfinite(m.vertices).all()
    normals=m.vertex_normals.copy();length=np.linalg.norm(normals,axis=1)
    # Opposed CAD seams can cancel the smoothed normal. Retain the surface
    # and use its largest incident face instead of exporting a zero normal.
    for index in np.flatnonzero(length<1e-12):
        incident=np.flatnonzero(np.any(m.faces==index,axis=1))
        face=incident[np.argmax(m.area_faces[incident])]
        triangle=m.vertices[m.faces[face]]
        normal=np.cross(triangle[1]-triangle[0],triangle[2]-triangle[0])
        normals[index]=normal/np.linalg.norm(normal)
    length=np.linalg.norm(normals,axis=1);assert (length>0).all(),key
    m.vertex_normals=normals/length[:,None]
    c=r.get('color')or[.17,.17,.17]
    rgb=colors.get(role_name,[round(255*(12.92*x if x<=.0031308 else 1.055*x**(1/2.4)-.055))for x in c[:3]]+[255])
    m.visual=trimesh.visual.TextureVisuals(material=PBRMaterial(name=role_name,baseColorFactor=rgb,metallicFactor=.68 if role_name in ['metal','frame','brass']else .06,roughnessFactor=.5,doubleSided=True))
    group='reference' if key in reference else 'head'if r['path'][1]=='NAUO8'else'fixed'
    m.metadata=dict(part_key=key,group=group,appearance_role=role_name)
    scene.add_geometry(m,geom_name='part_'+key,node_name='part_'+key)
    parts.append(dict(key=key,name=r['name'],group=group,appearance_role=role_name,native_bounds_mm=r['bounds_mm'],source_valid=r['valid'],native_adjustment_mm=shift))
    triangles+=len(m.faces)
    if len(parts)%100==0:print('SV08',len(parts),triangles,flush=True)
raw=scene.export(file_type='glb');(O/'model.glb.gz').write_bytes(gzip.compress(raw,9,mtime=0))
source=json.loads((R/'scripts/SV08_SOURCE.json').read_text(encoding='utf8'));source.pop('download_url',None)
manifest=dict(machine_id='sovol_sv08_350',source=source,parts=parts,triangles=triangles,native_leaf_count=len(rows),reference_leaves=sorted(reference),invalid_reference_leaves=[r['key']for r in rows if not r['valid']],removed_builtin_supports=[],display_adjustments=placements)
profile=dict(machine_id='sovol_sv08_350',title='SOVOL SV08 / 350',size=350,source=source,origin_mm=[-67.965,-62.653,153.7417],basis=[[1,0,0],[0,1,0],[0,0,1]],axes=dict(x=[0,0],y=[0,0],z=[0,0]),motions={},motion_preview=False,palette_defaults=dict(base='#24272c',accent='#3e67ab',frame='#23262a'))
for name,data in [('assembly_manifest.json',manifest),('machine_profile.json',profile)]:(O/name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
files={}
for name in ['assembly_manifest.json','machine_profile.json','model.glb.gz']:
    b=(O/name).read_bytes();spec=dict(path=O.name+'/'+name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    if name.endswith('.gz'):spec.update(encoding='gzip',decoded_bytes=len(raw),decoded_sha256=hashlib.sha256(raw).hexdigest())
    files['model.glb'if name.endswith('.gz')else name]=spec
(O/'INDEX.json').write_text(json.dumps(dict(machine_id='sovol_sv08_350',parts=len(parts),files=files),indent=2)+'\n')
print('DONE SV08',len(parts),triangles,len(raw),len((O/'model.glb.gz').read_bytes()),flush=True)
