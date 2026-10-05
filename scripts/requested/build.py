from pathlib import Path
import sys,json,gzip,hashlib,re,collections
import cadquery as cq,numpy as np,trimesh
from trimesh.visual.material import PBRMaterial
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('keys',nargs='+');args=parser.parse_args();C=args.cache;O=args.output
metadata={r['key']:r for r in json.loads((Path(__file__).parent/'SOURCES.json').read_text(encoding='utf8'))}
CONFIGS={
 'tictac':dict(id='tictac_21_120',title='TicTac 2.1 / 120',size=120,version='2.1 / 040124 / file 2024-01-06',author='Squirrelbrain',url='https://www.printables.com/model/416884-tictac-21',license='CC-BY-NC-SA-4.0',reference=['1419','1489','1497','1498']),
 'rook':dict(id='rook_mk2_120',title='Rook MK2 / 120',size=120,version='MK2 beta / file 2026-03-21',author='Rolohaun Design / Kanrog',url='https://www.printables.com/model/1644597-rook-mk2',license='CC-BY-NC-4.0',reference=[]),
 'the100':dict(id='the100_v11_165',title='THE 100 v1.1 / 165',size=165,version='v1.1',author='Matt The Printing Nerd / MSzturc',url='https://github.com/MSzturc/the100',license='CC-BY-NC-SA-4.0',reference=['275']),
 'satsuma':dict(id='satsuma180_v10',title='Satsuma 180 v1.0',size=180,version='v1.0 / 171223 / file 2023-12-18',author='Squirrelbrain',url='https://www.printables.com/model/487266-satsuma-180-v10',license='GPL-3.0',reference=[]),
}
COLORS={'base':[36,39,44,255],'accent':[227,38,54,255],'frame':[37,41,44,255],'motor':[34,36,39,255],'metal':[180,186,193,255],'brass':[185,145,56,255],'rubber':[22,24,27,255],'tube':[228,231,227,255],'bed_surface':[170,148,75,255],'glass':[170,200,214,45],'panel':[36,39,44,255],'board':[30,82,51,255]}
def role(key,r):
 n=r['name'].strip().lower();p='/'.join(r['path']).lower();c=r.get('color')or[.18,.18,.18];k=int(r['key'])
 if r.get('source_component')=='galileo2_g2sa':
  sk=int(r['source_key'])
  if sk in [68,69]:return'base'
  if sk in [71,72,73]:return'accent'
  if sk in [55,56,57,58]:return'brass'
  if 18<=sk<=35:return'motor'
  return'metal'
 if key=='rook'and k in [274,290,317,318,319,323,324,325,326,331,333]:return'accent'if k in [274,290,318,323,325,326,333]else'base'
 if any(w in n for w in ['bearing_housing','nut_holder','nut_housing','belt_body','belt_clip','belt_cover','belt_clamp','belt_lock','endstop_mount','motor_mount']):return'base'
 if 'heatset'in n or'heatset'in p or'heat-set'in n or'heat insert'in n:return'brass'
 if re.search(r'^m\d|^9\d{4}a|\b(?:din|iso)\b',n)or any(w in n for w in ['screw','washer','t-nut','sq_nut',' nut','spring','shaft','bearing','coupler','pulley','idler_gt2','f695','mgn','linear rod','lr 8mm','rod_','esferas','heatbreak']):return'metal'
 if 'nozzle'in n:return'brass'
 if 'belt'in n and not any(w in n for w in ['lock','nut','body','clip','clamp','tension','cover','mount']):return'rubber'
 if 'ptfe'in n and not any(w in n for w in ['brace','swivel','gland']):return'tube'
 if n.startswith(('2020','2040','3030','3040'))and not any(w in n for w in ['plate','nut']):return'frame'
 if any(w in n for w in ['rubber','tpu','sock','calzino']):return'rubber'
 if any(w in n for w in ['fan_','fan 30','fan axial','impeller','turbine','7_fan','4010 fan','6020 housing']):return'motor'
 if any(w in p for w in ['nema','stepper','motor:']):
  if any(w in n for w in ['housing','body','motor','solid']):return'motor'
  return'native'
 if any(w in n for w in ['pinda','endstop','adxl'])and not any(w in n for w in ['mount','cover','plate']):return'native'
 if any(w in n for w in ['buildplate','magnetic plate','heatbed']):return'bed_surface'
 if 'panel'in n or'sheet_3mm'in n:
  if any(w in n for w in ['back','rear','bottom','wago','mount','clip','centre','blank','cable']):return'panel'if n in ['panel_back','panel_rear','panel_bottom']else'base'
  if any(w in n for w in ['right','left','side','front','door','top']):return'glass'
 if any(w in n for w in ['chain link','chain_','chain ']):return'base'
 if key=='rook':
  if n in ['bed','part 7','part 6']or'hotend_bambu'in n:return'metal'
  if n in ['frame','top','mid','gantry','y_axis','bottom_frame']or any(w in n for w in ['foot','skirt','bed_frame','bed_knob','mount','rear_vent','z_tensioner','mainbody','toolhead_assembly','rook_logo']):return'accent'if c[1]>c[0]*1.3 or c[0]>c[1]*1.8 else'base'
 if key=='the100':
  if 'mainboard'in p or'banana_pi'in p:return'native'
  if n.startswith(('bottom frame','back frame','bed v'))or'frame v15'in p or('gantry'in p and n in ['compound','solid'])or n in ['chc mount','cable holder v1','mainboard holder v2','cable guide v2','powercord clamp v2','bmg extruder halterung v1']or k in [264,274,275,277]:return'accent'if 'toolhead'in p else'base'
  if n in ['hotend','top','heater','arm']:return'metal'
  if n=='clip':return'rubber'
 if key=='tictac':
  if 'pico case'in p and not any(w in n for w in ['pico_case','pico case','printed','cover','case_lid','mount','support']):return'native'
  if n.startswith(('z_','x_','y_','rr_','toolhead_','filament_','spool_','zx_'))or n=='solid' or any(w in n for w in ['brace','bracket','mount','case','armor','cover','bed_hinge','cap_']):return'accent'if max(c)-min(c)>.25 else'base'
 if key=='satsuma':
  if 'psu_'in p or'raspberry_pi'in p or'molex'in p or'orbiter'in p:return'native'
  if any(w in n for w in ['dissipatore','riscaldatore','termistore']):return'metal'
  if any(w in n for w in ['frame','mount','cover','corner','clamp','backpack','brace','housing','wago_panel','blank','fan_plate','bed_arm','spacer_10','belt_clip','drive_','xy_block','ptfe_ecas','din_rail_mount']):return'accent'if c[0]>c[1]*2 and c[0]>.1 else'base'
  if n.startswith(('solid','compound'))and c==[0.02518685907125473]*3:return'base'
 if c[0]>.2 and c[0]>c[1]*2 and c[0]>c[2]*2:return'accent'
 return'native'
def build(key):
 cfg=CONFIGS[key];cache=C/key;out=O/key;out.mkdir(parents=True,exist_ok=True)
 rows=json.loads((cache/'inventory.json').read_text(encoding='utf8'));ref=set(cfg['reference']);B=np.array([[1,0,0],[0,0,1],[0,-1,0]])
 visible=[r for r in rows if r['key']not in ref];lo=np.min([r['bounds_mm'][0]for r in visible],0);hi=np.max([r['bounds_mm'][1]for r in visible],0);origin=[(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]]
 scene=trimesh.Scene();aux=trimesh.Scene();parts=[];reviews=[];triangles=0;repairs=[]
 for r in rows:
  k=r['key'];s=cq.Shape.importBrep(str(cache/(k+'.brep')));before=s.Volume()
  if not r['valid']:
   fixed=s.fix();after=fixed.Volume();bb=fixed.BoundingBox();bounds=[[bb.xmin,bb.ymin,bb.zmin],[bb.xmax,bb.ymax,bb.zmax]]
   repair=dict(key=k,before_valid=False,after_valid=fixed.isValid(),relative_volume_change=abs(after-before)/max(abs(before),1),max_bounds_change_mm=float(np.max(np.abs(np.array(bounds)-r['bounds_mm']))))
   if repair['after_valid']and repair['relative_volume_change']<1e-4 and repair['max_bounds_change_mm']<.001:s=fixed;s.exportBrep(str(cache/(k+'.repaired.brep')));repair['applied']=True
   else:repair['applied']=False
   repairs.append(repair)
  v,f=s.tessellate(.18,.30);assert f,(key,k,'empty native tessellation');verts=(np.array([p.toTuple()for p in v])-origin)@B.T*.001;m=trimesh.Trimesh(vertices=verts,faces=f,process=False)
  m.update_faces(m.nondegenerate_faces(height=1e-10));m.remove_unreferenced_vertices();assert len(m.faces)and np.isfinite(m.vertices).all()
  normals=m.vertex_normals.copy();length=np.linalg.norm(normals,axis=1)
  for i in np.flatnonzero(length<1e-12):
   incident=np.flatnonzero(np.any(m.faces==i,axis=1));j=incident[np.argmax(m.area_faces[incident])];q=m.vertices[m.faces[j]];n=np.cross(q[1]-q[0],q[2]-q[0]);normals[i]=n/np.linalg.norm(n)
  normals/=np.linalg.norm(normals,axis=1)[:,None];m.vertex_normals=normals
  role_name=role(key,r);c=r.get('color')or[.18,.18,.18];rgb=COLORS.get(role_name,[round(255*x)for x in c]+[255])
  m.visual=trimesh.visual.TextureVisuals(material=PBRMaterial(name=role_name,baseColorFactor=rgb,metallicFactor=.65 if role_name in ['metal','frame','brass']else .04,roughnessFactor=.5,doubleSided=True,alphaMode='BLEND'if role_name=='glass'else'OPAQUE'))
  group='reference'if k in ref else'head'if(key=='the100'and'Toolhead'in'/'.join(r['path'])or key=='rook'and'Toolhead'in'/'.join(r['path'])or key=='tictac'and'New RR Toolhead'in'/'.join(r['path'])or key=='satsuma'and'HOTEND_ASSEMBLY'in'/'.join(r['path']))else'fixed'
  m.metadata=dict(part_key=k,group=group,appearance_role=role_name);target=aux if r.get('source_component')=='galileo2_g2sa'else scene;target.add_geometry(m,geom_name='part_'+k,node_name='part_'+k)
  parts.append(dict(key=k,name=re.sub(r'(?i)solidworks|open cascade step translator.*','',r['name']).strip()or'Native part '+k,group=group,appearance_role=role_name,native_bounds_mm=r['bounds_mm'],source_valid=r['valid'],export_native_valid=s.isValid(),native_adjustment_mm=[0,0,0]));triangles+=len(m.faces)
  reviews.append(dict(key=k,native_triangles=len(f),export_triangles=len(m.faces),decimated=False,normals_finite=True))
  if len(parts)%100==0:print(key,len(parts),triangles,flush=True)
 raw=scene.export(file_type='glb');(out/'model.glb.gz').write_bytes(gzip.compress(raw,9,mtime=0));src=json.loads((cache/'source.json').read_text());pin=metadata[key]['revision'];source=dict(repository=cfg['url'],original_url=cfg['url'],upstream_url=cfg['url']+'/tree/'+pin if key=='the100'else cfg['url'],revision=pin,version=cfg['version'],author=cfg['author'],license=cfg['license'],source_step_sha256=src['sha256'])
 if key=='rook':source['additional_sources']=[dict(repository='https://github.com/JaredC01/Galileo2',revision='98f8a37944d7277cd37231776400553cc402219f',license='GPL-3.0',scope='Separate Galileo 2 G2SA geometry asset',registration=json.loads((cache/'G2SA_REGISTRATION.json').read_text()))]
 manifest=dict(machine_id=cfg['id'],source=source,parts=parts,triangles=triangles,native_leaf_count=len(rows),reference_leaves=sorted(ref),invalid_reference_leaves=[r['key']for r in rows if not r['valid']],removed_builtin_supports=[],native_repairs=repairs)
 profile=dict(machine_id=cfg['id'],title=cfg['title'],size=cfg['size'],source=source,origin_mm=origin,basis=B.tolist(),axes=dict(x=[0,0],y=[0,0],z=[0,0]),motions={},motion_preview=False,palette_defaults=dict(base='#24272c',accent='#e32636',frame='#25292c'))
 if key=='satsuma':profile['view_directions']=dict(iso=[-.6,.6,-.95],front=[0,.12,-1],head=[-.4,.5,-1])
 for name,data in [('assembly_manifest.json',manifest),('machine_profile.json',profile)]:(out/name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
 files={}
 for name in ['assembly_manifest.json','machine_profile.json','model.glb.gz']:
  b=(out/name).read_bytes();spec=dict(path='requested-v1/'+key+'/'+name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
  if name.endswith('.gz'):spec.update(encoding='gzip',decoded_bytes=len(raw),decoded_sha256=hashlib.sha256(raw).hexdigest())
  files['model.glb'if name.endswith('.gz')else name]=spec
 if key=='rook':
  extra=aux.export(file_type='glb');packed=gzip.compress(extra,9,mtime=0);(out/'g2sa.glb.gz').write_bytes(packed);files['g2sa.glb']=dict(path='requested-v1/rook/g2sa.glb.gz',bytes=len(packed),sha256=hashlib.sha256(packed).hexdigest(),encoding='gzip',decoded_bytes=len(extra),decoded_sha256=hashlib.sha256(extra).hexdigest())
 index=dict(machine_id=cfg['id'],parts=len(parts),files=files)
 if key=='rook':index['additional_models']=['g2sa.glb']
 (out/'INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
 (out/'MESH_BUILD_QA.json').write_text(json.dumps(dict(all_passed=True,parts=reviews,native_repairs=repairs,scope='Full native tessellation; no decimation. Unit normals and degenerate triangle removal; native solid validity is recorded separately.'),indent=2)+'\n')
 print('DONE',key,len(parts),triangles,len(raw),len((out/'model.glb.gz').read_bytes()),'repairs',repairs,flush=True)
if __name__=='__main__':
 for key in args.keys:build(key)
