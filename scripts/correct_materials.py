from pathlib import Path
import json,struct,gzip,hashlib,copy
from convert_family import role,group,COLORS,CONFIGS
import sys
CACHE=Path(sys.argv[1]);OUTPUT=Path(sys.argv[2])
for key in CONFIGS:
 if not (OUTPUT/key/'model.glb.gz').exists():continue
 out=OUTPUT/key;rows={r['key']:r for r in json.loads((CACHE/key/'inventory.json').read_text(encoding='utf8'))};manifest=json.loads((out/'assembly_manifest.json').read_text(encoding='utf8'))
 raw=gzip.decompress((out/'model.glb.gz').read_bytes());jl,jt=struct.unpack_from('<II',raw,12);glb=json.loads(raw[20:20+jl]);tail=raw[20+jl:];roles={}
 for part in manifest['parts']:
  part['appearance_role']=role(key,rows[part['key']]);part['group']=group(key,rows[part['key']]);roles[part['key']]=part
 material_cache={}
 for mesh in glb['meshes']:
  k=mesh.get('extras',{}).get('part_key')
  if not k:continue
  r=roles[k];mesh['extras'].update(group=r['group'],appearance_role=r['appearance_role'])
  for primitive in mesh['primitives']:
   original=glb['materials'][primitive['material']]
   role_name=r['appearance_role'];rgb=COLORS.get(role_name)
   if not rgb:continue
   if role_name not in material_cache:
    mat=copy.deepcopy(original);mat['name']=role_name;linear=lambda c:c/255/12.92 if c/255<=.04045 else((c/255+.055)/1.055)**2.4
    mat['pbrMetallicRoughness'].update(baseColorFactor=[linear(c)for c in rgb[:3]]+[rgb[3]/255],metallicFactor=.65 if role_name in ['metal','frame','brass']else .08,roughnessFactor=.43 if role_name in ['metal','frame']else .62)
    mat['alphaMode']='BLEND'if role_name=='glass'else'OPAQUE';material_cache[role_name]=len(glb['materials']);glb['materials'].append(mat)
   primitive['material']=material_cache[role_name]
 jb=json.dumps(glb,separators=(',',':'),ensure_ascii=False).encode('utf8');jb+=b' '*((-len(jb))%4);raw=struct.pack('<III',0x46546c67,2,20+len(jb)+len(tail))+struct.pack('<II',len(jb),jt)+jb+tail
 (out/'model.glb.gz').write_bytes(gzip.compress(raw,9,mtime=0));(out/'assembly_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
 index=json.loads((out/'INDEX.json').read_text())
 for name,spec in index['files'].items():
  b=(out/Path(spec['path']).name).read_bytes();spec.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
  if name=='model.glb':spec.update(decoded_bytes=len(raw),decoded_sha256=hashlib.sha256(raw).hexdigest())
 (out/'INDEX.json').write_text(json.dumps(index,indent=2)+'\n');print('Material roles updated:',key)
