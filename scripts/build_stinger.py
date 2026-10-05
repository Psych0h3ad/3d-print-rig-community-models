"""Convert the pinned LH Stinger complete assembly, retaining native placements."""
from pathlib import Path
import argparse,json,gzip,hashlib,re
import cadquery as cq
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial
from native_mesh import clean_mesh,small_hardware

MACHINE='lh_stinger_200'
PIN='4fb1e2eb917bfe78ae29cbde5a3793a80c02cc80'
BASIS=[[1,0,0],[0,0,1],[0,-1,0]]
ORIGIN=[25.6015627891716,263.16013762433,-97.3065782729323]
COLORS={'base':[36,39,44,255],'accent':[227,38,54,255],'frame':[37,41,44,255],
        'metal':[180,186,193,255],'brass':[185,145,56,255],'motor':[34,36,39,255],
        'rubber':[22,24,27,255],'tube':[228,231,227,255],'bed_surface':[48,51,54,255]}

def group(r):
 p='/'.join(r['path']).lower();k=int(r['key'])
 if '/extras:' in p or k==13:return 'reference'
 if '/toolhead v220:' in p:return 'head'
 if '/accesories:1/aux fan:' in p:return 'beam'
 if k==550:return 'belt'
 if '/x:' in p:return 'beam'
 if '/y:1/y motion:' in p:return 'bed'
 if k==708:return 'belt'
 if k==345:return 'compound_motion'
 if k in [332,333,338,343]:return 'tube'
 if k in [341,344]:return 'beam'
 return 'fixed'

def role(r):
 n=r['name'].lower();p='/'.join(r['path']).lower();k=int(r['key'])
 if k in [267,549,778] or any(s in n for s in ['joining plate','cast 90 degree corner']):return 'frame'
 if k==659 or n.startswith('cf bed'):return 'bed_surface'
 if k in [372,399,441,483,550,668,682,708] or n=='wires' or n.startswith(('cable ','toolhead cable','cordropecoil')):return 'rubber'
 if k==332 or n.startswith('bowden 27'):return 'tube'
 if k==18 or 'heat insert' in n:return 'brass'
 if re.search(r'screw|washer|t-nut|\bnut\b|bearing|shaft|spring|pulley|magnet',n):return 'metal'
 if 'mgn12' in p or n.startswith('rail'):return 'metal'
 if 'nema' in p or 'ldo_36sth' in p or n.startswith(('fan blower','sunon')) or 'radial-cooling-fan' in p:return 'motor'
 if 'phaetus dragon' in p:return 'brass' if 'nozzle' in n else 'metal'
 if 'pcb' in p or 'adxl345' in p or 'omron' in n or 'limitswitch' in p and n.startswith('switch'):return 'native'
 if 'orbiter' in p:
  if any(s in p for s in ['gearset','brasscoupler']):return 'metal'
  return 'base'
 if 'rubber foot' in n:return 'rubber'
 if k==345:return 'base'
 c=r['color']
 if c and c[0]>.25 and c[0]>c[1]*2 and c[0]>c[2]*2:return 'accent'
 return 'base'

def main():
 a=argparse.ArgumentParser();a.add_argument('--cache',type=Path,required=True);a.add_argument('--output',type=Path,required=True);args=a.parse_args()
 rows=json.loads((args.cache/'inventory.json').read_text());src=json.loads((args.cache/'source.json').read_text());assert src['revision']==PIN
 out=args.output;out.mkdir(parents=True,exist_ok=True);scene=trimesh.Scene();parts=[];triangles=0
 for r in rows:
  key=r['key'];shape=cq.Shape.importBrep(str(args.cache/(key+'.brep')));rn=role(r);g=group(r)
  pieces=shape.Solids() if key=='16' else [shape]
  if key=='16':scene.graph.update(frame_from=scene.graph.base_frame,frame_to='part_16',matrix=np.eye(4),metadata=dict(part_key=key,group=g,appearance_role=rn))
  for i,piece in enumerate(pieces):
   pr='rubber'if key=='16'and i==1 else rn
   vertices,faces=piece.tessellate(.2,.3)
   coords=(np.array([v.toTuple() for v in vertices])-np.array(ORIGIN))@np.array(BASIS).T*.001
   mesh=trimesh.Trimesh(vertices=coords,faces=faces,process=False)
   if not mesh.is_winding_consistent:trimesh.repair.fix_winding(mesh)
   mesh=clean_mesh(mesh,small_hardware(r['name'],pr))
   c=r['color'] or [.1,.1,.1];rgb=COLORS.get(pr,[round(255*(12.92*x if x<=.0031308 else 1.055*x**(1/2.4)-.055))for x in c]+[255])
   mesh.visual=trimesh.visual.TextureVisuals(material=PBRMaterial(name=pr,baseColorFactor=rgb,metallicFactor=.65 if pr in ['metal','frame','brass']else .05,roughnessFactor=.45 if pr in ['metal','frame']else .65,doubleSided=True))
   mesh.metadata=dict(appearance_role=pr)if key=='16'else dict(part_key=key,group=g,appearance_role=rn)
   name='part_'+key+('_body_'+str(i)if key=='16'else '')
   scene.add_geometry(mesh,geom_name=name,node_name=name,parent_node_name='part_16'if key=='16'else None);triangles+=len(mesh.faces)
  path=r['path'][1:];parts.append(dict(key=key,name=r['name'],source_path=path,native_bounds_mm=r['bounds_mm'],group=g,appearance_role=rn,source_valid=r['valid']))
  if key=='345':parts[-1]['native_body_motions']={'4':'beam'}
  if len(parts)%100==0:print('Stinger',len(parts),triangles,flush=True)
 raw=scene.export(file_type='glb',include_normals=True);(out/'model.glb.gz').write_bytes(gzip.compress(raw,9,mtime=0))
 source=dict(repository='https://github.com/lhndo/LH-Stinger',revision=PIN,version='LH Stinger 1.0 · assembly v23 / toolhead v220',path='CAD/Printer/LH Stinger.step.zip',license='CC-BY-NC-SA-4.0',source_step_sha256=src['sha256'])
 manifest=dict(machine_id=MACHINE,source=source,parts=parts,triangles=triangles,native_leaf_count=len(rows),reference_leaves=[p['key']for p in parts if p['group']=='reference'],invalid_source_leaves=[r['key']for r in rows if not r['valid']])
 profile=dict(machine_id=MACHINE,title='LH Stinger / 200',size=200,build_volume_mm=[200,200,200],source=source,origin_mm=ORIGIN,basis=BASIS,axes=dict(x=[-95,95],y=[-105,105],z=[-61.7872851403,130]),motions=dict(head=['x',0,'z'],beam=[0,0,'z'],bed=[0,'y',0]),palette_defaults=dict(base='#24272c',accent='#e32636',frame='#25292c'))
 manifest['standard_hotend']='Dragon HF / extension adapter / extended nozzle';manifest['parts'][16]['native_body_materials']={'1':'rubber'}
 profile['standard_hotend']=manifest['standard_hotend'];profile['clearance_datums_mm']=dict(bed_top_z=-.6092100609,nozzle_tip_z=61.3012571097,lowest_bed_overlapping_part_z=61.2280750794,minimum_gap=.05)
 for name,data in [('assembly_manifest.json',manifest),('machine_profile.json',profile)]:
  (out/name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
 files={}
 for name in ['assembly_manifest.json','machine_profile.json','model.glb.gz']:
  data=(out/name).read_bytes();spec=dict(path='stinger/'+name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
  if name.endswith('.gz'):spec.update(encoding='gzip',decoded_bytes=len(raw),decoded_sha256=hashlib.sha256(raw).hexdigest())
  files['model.glb' if name.endswith('.gz') else name]=spec
 (out/'INDEX.json').write_text(json.dumps(dict(machine_id=MACHINE,parts=len(parts),files=files),indent=2)+'\n')
 print('DONE',len(parts),triangles,len(raw),files['model.glb']['bytes'],flush=True)

if __name__=='__main__':main()
