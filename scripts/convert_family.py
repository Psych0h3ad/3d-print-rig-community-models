from pathlib import Path
import sys,json,gzip,hashlib,re
import cadquery as cq,numpy as np,trimesh
from trimesh.visual.material import PBRMaterial
from native_mesh import clean_mesh,small_hardware
CACHE=Path(sys.argv[1]);OUTPUT=Path(sys.argv[2])
VM_PRINTED={'40mm_fan_cage','3030_endcap','3030_spool_holder','back_cartesian','bmo_face','bmo_support','bottom_mgn12_short_duct','case_back','case_front','case_feet','case_front_panel','case_back_panel','cartesian_cable_fin','electronics_case_wire_guide','lj8_probe_mount_8mm','pillow_block','ratrig_eva_shroud','top_endstop_angled','top_mgn12_lgx_lite','trihorn_duct','universal_face','tension_slider_6mm_belt_m3s','x_gantry_end_cap','x_wire_holder','x_idler','x_motor_cage','y_belt_cover','y_belt_mount','y_belt_tensioner','z_cap'}
VM_PRINTED.update({'side_legs','z_motor_cage','y_motor_cage','y_idler','3030_end_cap','y_endstop_mount'})
CONFIGS={
 'aether':dict(id='antithesis_aether_mk11',title='Antithesis Aether MK1.1',size=130,dimensions=[130,100,115.5],version='MK1.1 · aluminum gantry · release build v3',folder='Antithesis-Aether-MK1.1',origin=[-44,-500,-67],basis=[[0,-1,0],[0,0,1],[-1,0,0]],axes=dict(x=[-60,60],y=[-50,50],z=[0,110]),motions=dict(head=[0,0,'z'],beam=['y',0,0],bed=['y','x',0]),license='GPL-3.0'),
 'vminion':dict(id='ratrig_vminion_180',title='Rat Rig V-Minion / 180',size=180,dimensions=[180,180,180],version='V-Minion 1.0 · official assembly revision 7',folder='V-Minion',origin=[70,0,0],basis=[[1,0,0],[0,0,1],[0,-1,0]],axes=dict(x=[0,180],y=[0,180],z=[0,175]),motions=dict(head=['x',0,'z'],beam=[0,0,'z'],bed=[0,'y',0]),license='CC-BY-NC-SA-4.0'),
 'snake180':dict(id='snakeoil_xy_180',title='SnakeOil XY / 180',size=180,dimensions=[180,180,180],version='v1 · 180 assembly · Mosquito / Sherpa Mini',folder='SnakeOil-XY',origin=[0,160,0],basis=[[1,0,0],[0,0,1],[0,-1,0]],axes=dict(x=[-90,90],y=[-110,60],z=[-70,120]),motions=dict(head=['x','y',0],beam=[0,'y',0],bed=[0,0,'z']),license='GPL-3.0 + ANNEX Engineering License'),
 'snakeidex':dict(id='snakeoil_xy_idex',title='SnakeOil XY / IDEX',size=250,dimensions=[250,240,230],version='v1 · IDEX assembly · dual Mosquito / Sherpa Mini',folder='SnakeOil-XY',origin=[40,140,0],basis=[[1,0,0],[0,0,1],[0,-1,0]],axes=dict(x=[0,90],u=[0,80],y=[-130,70],z=[-70,170]),motions=dict(head=['x','y',0],head2=['u','y',0],beam=[0,'y',0],bed=[0,0,'z']),license='GPL-3.0 + ANNEX Engineering License'),
 'snake3s':dict(id='snakeoil_3s_kp3s_180',title='SnakeOil XY-3S / KP3S',size=180,dimensions=[180,180,180],version='v1 · KP3S conversion · V6 / Sherpa Mini',folder='SnakeOilXY-3S',origin=[-43,-156,40],basis=[[1,0,0],[0,1,0],[0,0,1]],axes=dict(x=[-70,70],y=[-70,70],z=[-65,100]),motions=dict(head=['x','z',0],beam=[0,'z',0],bed=[0,0,'y']),license='GPL-3.0 + ANNEX Engineering License'),
 'proosa':dict(id='snakeoil_proosaxy',title='ProosaXY / MK3-S conversion',size=250,dimensions=[250,210,210],version='MAIN assembly · triple Z · V6 / Sherpa Mini',folder='ProosaXY',origin=[185,180,0],basis=[[1,0,0],[0,0,1],[0,-1,0]],axes=dict(x=[-110,110],y=[-140,80],z=[-55,115]),motions=dict(head=['x','y',0],beam=[0,'y',0],bed=[0,0,'z']),license='GPL-3.0 + ANNEX Engineering License'),
}
def group(key,r):
 n=r['name'].lower();p='/'.join(r['path']).lower();k=int(r['key']);a,b=r['bounds_mm']
 if key=='aether':
  if 'build helpers:' in p or k in [158,209,210,499]:return 'reference'
  if 'toolhead assembly:' in p or 'printhead mount assembly:' in p:return 'head'
  if k==347:return 'belt'
  if 'aluminum x axis assembly:' in p or 'bed assembly 13x10cm pcb:' in p:return 'bed'
  if 'aluminum y carriage assembly:' in p:return 'beam'
 if key=='vminion':
  if 'eva assembly' in p:return 'head'
  if n.startswith('x-axis 2gt'):return 'belt'
  if 'x-axis assembly' in p:return 'beam'
  if 'y-axis & bed assembly' in p:return 'bed'
 if key=='snake3s':
  if 'toolhead-direct-drive' in p or k in [116,123,124,125]:return 'head'
  if r['path'][1] in ['X-frame','x-motor-mount','x-tesioner','oldham-coupler']:return 'beam'
  if 126<=k<=134:return 'bed'
 if key in ['snake180','snakeidex']:
  top=r['path'][1].lower();child=r['path'][2].lower() if len(r['path'])>2 else ''
  if key=='snakeidex' and 'sherpa-mini:2' in r['path']:return 'reference'
  if top.startswith('xy-axis'):
   if 'toolhead' in child:return 'head2' if key=='snakeidex' and child.endswith(':2') else 'head'
   if child.startswith('sherpa-mini')or child.startswith('extruder-cable-mounter'):return 'head'
   if child.startswith('xy-belt'):return 'belt'
   if child.startswith('y-carrier')or child.startswith(('x-endstop-flag','y drives','y tensioning idlers')):return 'beam'
   if child.startswith('x_rail'):
    if 'block'in n:return 'head2'if key=='snakeidex'and k==1022 else 'head'
    return 'beam'
   if child.startswith('y_rails')and 'block'in n:return 'beam'
  if top.startswith('z-axis'):
   if child.startswith(('bed_','z-rail-block-mount')) or child.startswith('z_rails')and'block'in n:return 'bed'
 if key=='proosa':
  if r['path'][1]=='toolhead':return 'head'
  if r['path'][1]=='xy-axis' and ('y-carrier' in p or n.startswith('370mm-shaft')):return 'beam'
  if r['path'][1]=='z-axis'and r['path'][2]=='bed-stack':return 'bed'
 return 'fixed'
def role(key,r):
 n=r['name'].lower().strip('_ ');p='/'.join(r['path']).lower();k=int(r['key']);a,b=r['bounds_mm'];c=r['color']or[.2,.2,.2]
 if key=='snakeidex'and 0<=k<=17:return 'frame'
 if key=='vminion' and re.sub(r' v[\d.]+$','',n)in VM_PRINTED:return 'accent'if any(w in n for w in ['duct','face','slider','cage','idler'])else'base'
 if key=='vminion'and n.startswith(('t-slot ','joining plate ','cast 90 degree corner bracket ')):return 'frame'
 if key=='vminion'and n.startswith('rubber foot '):return 'rubber'
 if key=='vminion' and n.startswith('v-minion-')and'plate'in n:return 'frame'
 if key=='vminion'and n=='solid'and'idler pulley'in p:return 'metal'
 if 'hand_twisted_nut'in n:return 'base'
 if key in ['snake180','snakeidex','snake3s','proosa']:
  if k in {'snake180':{411,412,488,572},'snakeidex':{343,373,374,478,491,518,530},'snake3s':set(),'proosa':set()}[key]:return 'base'
  if re.search(r'bearing[-_]mount|hinge|gasket|housing|casing|strain-relief|cable-end|spool-(?:roller|end|base)|idler-(?:top|bottom|mid)|^y idler|umbilical splitter|probe dock|handle|lcd-base|reset-button|eject-level|^fs_lever|^(?:cw|camera)-axis',n):return 'base'
  if re.search(r'idler_gear|filament_gear',n):return 'metal'
  if 'active-carbon-foam'in n:return 'rubber'
 if key in ['snake180','snakeidex','snake3s','proosa'] and re.search(r'rail.*(?:mount|holder)|(?:mount|holder).*rail',n):return 'base'
 if re.search(r'heat.?set|insert',n)and not re.search(r'holder|mount|bracket',n):return 'brass'
 if re.search(r'\b(?:lm\d|mr\d)|threaded.?rod|eccentric_column|shim|^brass-tube',n):return 'brass'if'brass-tube'in n else'metal'
 if n in ['sink','break','block']:return 'metal'
 if re.search(r'(?:2020|2040|1515)[-_]',n)and not re.search(r'cap|mount|holder|foot',n):return 'frame'
 if key in ['snake180','snakeidex','proosa'] and re.fullmatch(r'\d+mm(?:-tap)?\d*',n):return 'frame'
 if re.search(r'^m\d|\b(?:din|iso)\b|\bnut\b|\bwasher\b|screw|bearing|pillow|shield|standoff|pulley|idler$|20t|ring terminals|shaft|coupler|(?:mgn|sse).*?(?:block|carriage|rail)|rail|^\d{4,}a\d+',n):return 'metal'
 if 'belt'in n and not any(w in n for w in ['mount','block','clamp','cover','tension','anchor']):return 'rubber'
 if 'ptfe'in n and not any(w in n for w in ['mount','holder','wear surface']):return 'tube'
 if re.search(r'nema|motor|stepper|fan .*brushless|(?:4010|5015|4028)[- ](?:fan|blower)|\d+x\d+x\d+ fan',n) and not re.search(r'mount|cage|bracket|support|shroud',n):return 'motor'
 if re.search(r'nozzle|ring gear|spur.?gear|drive.?gear|grab ring|heater cartridge|heat.?break|heatsink|mosquito-hotend|e3d-v6|conch mockup',n):return 'brass'if'nozzle'in n else 'metal'
 if key=='aether'and'frame bracket'in n:return 'base'
 if re.search(r'extrusion|v.slot|^\d{4}-\d|frame_bracket|frame bracket',n):return 'frame'
 if re.search(r'pcb|btt|bigtreetech|mks_robin|manta|skr |ebb|raspberry',p) and any(w in p for w in ['board','robin','skr ','manta m5p mockup','eb36','ebb36']):return 'native'
 if key=='aether':
  if 'ldo stepper'in p:return 'motor'
  if n.startswith('aluminum'):return 'frame'
  if k in [391,431]:return 'bed_surface'
  if 'spool mockup'in p:return 'native'
  if any(w in n for w in ['mount','bracket','body','plate','cover','clip','case','holder','carrier','carriage','tension','knob','arm','conduit','shroud','handle','adapter']):return 'accent'if any(w in n for w in ['adapter','fan mount','knob','probe mount','tensioner'])else'base'
 if key=='vminion':
  if 'lgx lite'in p:return 'motor'if 'motor'in n else'native'
  if 'phaetus dragonfly'in p or'keenovo'in n:return 'metal'if'phaetus'in p else'rubber'
  if 'pei sheet'in n:return 'bed_surface'
  if 'panel'in n:return 'glass'if'side'in n else'panel'
  if any(w in n for w in ['top_mgn','back_cartesian','universal_face','bottom_mgn','bmo_','trihorn','cartesian_cable','eva_shroud','probe_mount','tension_slider','endstop_angled','x_motor_cage','x_idler_cage','y_belt_','pillow_block','wire_guide','case_','spool_holder','endcap']):return 'accent'if any(w in n for w in ['duct','face','slider','cage'])else'base'
 if key=='snake3s':
  if 'bed_sheet'in n:return 'bed_surface'
  if n.startswith('base_')or n.startswith(('bed_frame','bed_heater','head_bracket','x_motor_bracket','z_nut_bracket')):return 'panel'if'base_'in n else'metal'
  if '2040'in n:return 'frame'
  if 'sherpa_mini_gear'in n or'filament_gear'in n or'idler_gear'in n:return 'metal'
  if n.startswith('rollers'):return 'rubber'
 if key in ['snake180','snakeidex','snake3s','proosa']:
  if key=='proosa'and n.startswith('mk52 bed'):return 'bed_surface'
  if 'aluminum-plate'in n:return 'metal'
  if 'panel'in n and not any(w in n for w in ['clip','mount','support','spacer','connector']):return 'glass'if any(w in '/'.join(r['path'][1:]).lower()for w in ['front-panel','left-panel','right-panel','side','top-panel'])else'panel'
  if n in ['side','back-panel']:return 'glass'if n=='side'else'panel'
  if 'fan'in n and not any(w in n for w in ['mount','duct','plate','cover']):return 'motor'
  if 'silicon' in n or'o-ring'in n:return 'rubber'
  if key=='proosa'and any(w in n for w in ['prusa','mk3-bed-frame','psu','e3d-v6']):return 'metal'
  if 'board:'in p or 'bigtreetech'in p:return 'native'
  if n.startswith(('ss_','_ss_','sse','_sse')):return 'metal'
  if n.startswith(('top00','middle00','spacer_m4')):return 'metal'
  if re.search(r'mount|mounter|support|duct|arm|holder|knob|sherpa-body|sherpa-arm|sherpa-knob|back-body|front-body|clamp|carriage|carrier|tesion|tension|cap|face|clip|cover|bracket|foot|spacer|flag|joint|connector|plate|block|guide',n):return 'accent'if any(w in n for w in ['duct','tension','tesion','knob','face','y-carrier-top','front-body'])else'base'
 if any(w in n for w in ['rubber','magnet','silicone','filament']):return 'rubber'if'filament'not in n else'native'
 return 'native'
COLORS={'glass':[170,200,214,48],'panel':[36,39,44,255],'base':[36,39,44,255],'accent':[227,38,54,255],'frame':[37,41,44,255],'motor':[34,36,39,255],'metal':[180,186,193,255],'brass':[185,145,56,255],'rubber':[22,24,27,255],'tube':[228,231,227,255],'bed_surface':[66,70,74,255]}
def build(key):
 cfg=CONFIGS[key];cache=CACHE/key;out=OUTPUT/key;out.mkdir(parents=True,exist_ok=True)
 rows=json.loads((cache/'inventory.json').read_text(encoding='utf8'));scene=trimesh.Scene();parts=[];triangles=0;B=np.array(cfg['basis']);origin=np.array(cfg['origin'])
 for r in rows:
  k=r['key'];s=cq.Shape.importBrep(str(cache/(k+'.brep')));v,f=s.tessellate(.2,.3)
  if not f:raise RuntimeError('Empty leaf '+key+'/'+k)
  verts=(np.array([p.toTuple()for p in v])-origin)@B.T*.001;rn=role(key,r);g=group(key,r);m=trimesh.Trimesh(vertices=verts,faces=f,process=False)
  m=clean_mesh(m,small_hardware(r['name'],rn))
  c=r['color']or[.18,.18,.18];rgb=COLORS.get(rn,[round(255*(12.92*x if x<=.0031308 else 1.055*x**(1/2.4)-.055))for x in c[:3]]+[255])
  m.visual=trimesh.visual.TextureVisuals(material=PBRMaterial(name=rn,baseColorFactor=rgb,metallicFactor=.65 if rn in ['metal','frame','brass']else .08,roughnessFactor=.43 if rn in ['metal','frame']else .62,doubleSided=True,alphaMode='BLEND'if rn=='glass'else'OPAQUE'));m.metadata=dict(part_key=k,group=g,appearance_role=rn)
  scene.add_geometry(m,geom_name='part_'+k,node_name='part_'+k)
  title=re.sub(r'[A-Z]:[\\/].*','',r['name']).strip()or'Native part '+k
  parts.append(dict(key=k,name=title,group=g,appearance_role=rn,native_bounds_mm=r['bounds_mm'],source_valid=r['valid'],native_adjustment_mm=[0,0,0],source_path=r['path']))
  triangles+=len(m.faces)
  if len(parts)%100==0:print(key,len(parts),triangles,flush=True)
 raw=scene.export(file_type='glb',include_normals=True);(out/'model.glb.gz').write_bytes(gzip.compress(raw,9,mtime=0));src=json.loads((cache/'source.json').read_text());source=dict(repository='https://github.com/'+src['repository'],revision=src['revision'],version=cfg['version'],path=src['path'],license=cfg['license'],source_step_sha256=src['sha256'])
 if key=='vminion':source.update(cad_url=src['path'],cad_revision=src['share_version'])
 manifest=dict(machine_id=cfg['id'],source=source,parts=parts,triangles=triangles,native_leaf_count=len(rows),reference_leaves=[p['key']for p in parts if p['group']=='reference'],invalid_reference_leaves=[r['key']for r in rows if not r['valid']])
 profile=dict(machine_id=cfg['id'],title=cfg['title'],size=cfg['size'],build_volume_mm=cfg['dimensions'],source=source,origin_mm=cfg['origin'],basis=cfg['basis'],axes=cfg['axes'],motions=cfg['motions'],palette_defaults=dict(base='#24272c',accent='#e32636',frame='#25292c'))
 if key=='snakeidex':profile.update(axis_labels=dict(u='X2'),head_groups=['head','head2'])
 for name,data in [('assembly_manifest.json',manifest),('machine_profile.json',profile)]: (out/name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
 files={}
 for name in ['assembly_manifest.json','machine_profile.json','model.glb.gz']:
  b=(out/name).read_bytes();spec=dict(path=key+'/'+name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
  if name.endswith('.gz'):spec.update(encoding='gzip',decoded_bytes=len(raw),decoded_sha256=hashlib.sha256(raw).hexdigest())
  files['model.glb'if name.endswith('.gz')else name]=spec
 (out/'INDEX.json').write_text(json.dumps(dict(machine_id=cfg['id'],parts=len(parts),files=files),indent=2)+'\n');print('DONE',key,len(parts),triangles,len(raw),len((out/'model.glb.gz').read_bytes()),flush=True)
if __name__=='__main__':
 for key in sys.argv[3:]:build(key)
