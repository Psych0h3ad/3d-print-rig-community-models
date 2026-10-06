"""Repair the tube using the actual cylindrical bore in custom-voron-v1 BREP.

Usage: python scripts/repair_custom_ptfe.py <extracted-custom-native-source>
The source directory contains the four machine directories from the v1 archive.
Unchanged models stay in v1; changed Trident models are written to v2.
"""
from pathlib import Path
import argparse, gzip, hashlib, json, math, shutil, struct
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepMesh import BRepMesh_IncrementalMesh
import numpy as np
import trimesh

ap=argparse.ArgumentParser()
ap.add_argument('native_source',type=Path)
args=ap.parse_args()
ROOT=Path(__file__).resolve().parents[1]
sha=lambda data:hashlib.sha256(data).hexdigest()
read=lambda file:json.loads(file.read_text(encoding='utf8'))
reports=[]
for mid in ['voron_trident_500_custom','voron_trident_350_half_z']:
    original=ROOT/'site/custom-voron-v1'/mid
    native=args.native_source/mid
    dest=ROOT/'site/custom-voron-v2'/mid
    dest.mkdir(parents=True,exist_ok=True)
    manifest=read(original/'assembly_manifest.json')
    rows={row['key']:row for row in manifest['parts']}
    spec=manifest['custom_ptfe']
    holder_key='voron_trident_350_base_1393'
    holder_file=native/rows[holder_key]['file']
    holder=cq.Shape.importBrep(str(holder_file))
    # The PTFE bore is two trimmed halves of the same R2.1 cylinder.
    faces=[]
    for face in holder.Faces():
        if face.geomType()!='CYLINDER':continue
        c=BRepAdaptor_Surface(face.wrapped).Cylinder()
        axis=np.array(c.Axis().Direction().Coord())
        if abs(c.Radius()-2.1)<1e-6 and abs(axis[1])>.9:
            faces.append((face,c))
    assert len(faces)==2, 'Expected the two native PTFE bore faces'
    axis=np.array(faces[0][1].Axis().Direction().Coord())
    if axis[1]<0:axis=-axis
    origin=np.array(faces[0][1].Location().Coord())
    # Area-weighted face centre projected onto the analytic bore axis.
    centre=sum(np.array(f.Center().toTuple())*f.Area() for f,c in faces)/sum(f.Area() for f,c in faces)
    end=origin+axis*np.dot(centre-origin,axis)
    old=np.array(spec['controls_mm'][-1])
    before=holder.distance(cq.Vertex.makeVertex(*old))
    controls=[list(p) for p in spec['controls_mm']]
    start=np.array(controls[0])
    # Clear the native rear chain mount before bending towards the roof port.
    controls[0]=(start+[0,0,40]).tolist()
    controls[1]=(start+[0,0,70]).tolist()
    # Keep the last 16 mm straight through the bore: a Bezier endpoint on the
    # centre alone can still clip the entry rim before it reaches that endpoint.
    entry=end+axis*16
    controls[-1]=entry.tolist()
    controls[-2]=(entry+axis*60).tolist()
    wire=cq.Wire.assembleEdges([
        cq.Edge.makeLine(cq.Vector(*start),cq.Vector(*controls[0])),
        cq.Edge.makeBezier([cq.Vector(*p) for p in controls[:4]]),
        cq.Edge.makeLine(cq.Vector(*controls[3]),cq.Vector(*controls[4])),
        cq.Edge.makeBezier([cq.Vector(*p) for p in controls[4:]]),
        cq.Edge.makeLine(cq.Vector(*entry),cq.Vector(*end))])
    tube=cq.Solid.sweep(cq.Wire.makeCircle(2,cq.Vector(*start),cq.Vector(0,0,1)),
                       [cq.Wire.makeCircle(1.5,cq.Vector(*start),cq.Vector(0,0,1))],
                       wire,makeSolid=True,isFrenet=False)
    assert tube.isValid()
    overlap=abs(tube.intersect(holder).Volume())
    assert overlap<.003, (mid,'PTFE clips holder',overlap)
    static_clearances=[]
    bb=tube.BoundingBox()
    for row in manifest['parts']:
        if row['key']==spec['part_key']:continue
        lo,hi=row['bounds_mm']
        if any(a>b or c<d for a,b,c,d in zip([bb.xmin,bb.ymin,bb.zmin],hi,[bb.xmax,bb.ymax,bb.zmax],lo)):continue
        shape=cq.Shape.importBrep(str(native/row['file']))
        volume=abs(tube.intersect(shape).Volume())
        static_clearances.append(dict(part_key=row['key'],overlap_mm3=volume))
        assert volume<.003,(mid,'PTFE static interference',row['key'],row['name'],volume)
    bore_error=np.linalg.norm(np.cross(end-origin,axis))
    assert bore_error<1e-8
    # A 4 mm annular tube inside a 4.2 mm bore retains 0.1 mm radial clearance.
    assert abs(holder.distance(cq.Vertex.makeVertex(*end))-2.1)<.001
    brep=dest/'ptfe.brep';tube.exportBrep(str(brep))
    raw=gzip.decompress((original/'model.glb.gz').read_bytes())
    length,kind=struct.unpack_from('<II',raw,12)
    gltf=json.loads(raw[20:20+length]);offset=20+length
    blen,bkind=struct.unpack_from('<II',raw,offset)
    binary=bytearray(raw[offset+8:offset+8+blen])
    def append(array,atype):
        binary.extend(b'\0'*((-len(binary))%4))
        view=len(gltf['bufferViews'])
        gltf['bufferViews'].append(dict(buffer=0,byteOffset=len(binary),byteLength=array.nbytes))
        binary.extend(array.tobytes())
        accessor=dict(bufferView=view,componentType=5126 if atype=='VEC3' else 5125,count=len(array),type=atype)
        if atype=='VEC3':accessor.update(min=array.min(axis=0).tolist(),max=array.max(axis=0).tolist())
        index=len(gltf['accessors']);gltf['accessors'].append(accessor)
        return index
    # CadQuery's default uses *relative* deflection, which produced >100 mm
    # skinny triangles on this long 4 mm tube. Pin an absolute CAD tolerance.
    BRepMesh_IncrementalMesh(tube.wrapped,.05,False,.1,True)
    vv,ff=tube.tessellate(.05,.1)
    mesh=trimesh.Trimesh(vertices=np.array([v.toTuple() for v in vv])[:,[0,2,1]]*[.001,.001,-.001],faces=ff,process=False)
    node=next(n for n in gltf['nodes'] if n.get('extras',{}).get('part_key')==spec['part_key'] and 'mesh' in n)
    primitive=gltf['meshes'][node['mesh']]['primitives'][0]
    primitive.update(attributes={'POSITION':append(np.asarray(mesh.vertices,dtype='<f4'),'VEC3'),
                                 'NORMAL':append(np.asarray(mesh.vertex_normals,dtype='<f4'),'VEC3')},
                     indices=append(np.asarray(mesh.faces,dtype='<u4').reshape(-1),'SCALAR'),mode=4)
    gltf['buffers'][0]['byteLength']=len(binary)
    binary.extend(b'\0'*((-len(binary))%4))
    j=json.dumps(gltf,separators=(',',':')).encode();j+=b' '*((-len(j))%4)
    raw=struct.pack('<III',0x46546c67,2,28+len(j)+len(binary))+struct.pack('<II',len(j),kind)+j+struct.pack('<II',len(binary),bkind)+binary
    (dest/'model.glb.gz').write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))
    bb=tube.BoundingBox()
    rows[spec['part_key']].update(bounds_mm=[[bb.xmin,bb.ymin,bb.zmin],[bb.xmax,bb.ymax,bb.zmax]],
                                native_sha256=sha(brep.read_bytes()),method='native_PTFE_holder_bore_registered_v2')
    spec.update(controls_mm=controls,start_mm=start.tolist(),end_mm=end.tolist(),holder_part_key=holder_key,holder_bore_axis=axis.tolist(),holder_bore_point_mm=origin.tolist(),route_revision=2)
    manifest['notices'].append('PTFE v2: spool-side tube terminates inside the measured 4.2 mm native holder bore; the old floating endpoint is corrected. Flexible movement remains a geometric preview, without constant-length or bend-radius certification.')
    (dest/'assembly_manifest.json').write_text(json.dumps(manifest,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
    shutil.copyfile(original/'machine_profile.json',dest/'machine_profile.json')
    report=dict(machine_id=mid,passed=True,old_endpoint_mm=old.tolist(),old_endpoint_distance_to_holder_mm=before,
                endpoint_mm=end.tolist(),native_holder_sha256=sha(holder_file.read_bytes()),tube_native_sha256=sha(brep.read_bytes()),
                bore_axis=axis.tolist(),bore_point_mm=origin.tolist(),bore_axis_error_mm=float(bore_error),
                native_holder_interference_mm3=overlap,radial_clearance_mm=.1,
                static_native_clearances=static_clearances,
                model_sha256=sha(raw),compressed_model_sha256=sha((dest/'model.glb.gz').read_bytes()),
                scope='Actual analytic holder bore registration, tangent alignment, native tube validity and exact tube/holder solid intersection. No full swept-machine clearance or constant-length claim.')
    reports.append(report)
    print(mid,'floating endpoint gap',round(before,3),'mm; corrected overlap',overlap,flush=True)
(ROOT/'reviews/CUSTOM_PTFE_NATIVE_QA.json').write_text(json.dumps(dict(all_passed=True,results=reports),indent=2)+'\n',newline='\n')
