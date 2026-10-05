from pathlib import Path
import json,hashlib,cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--rook',type=Path,required=True);parser.add_argument('--galileo',type=Path,required=True);args=parser.parse_args();C=args.rook;G=args.galileo
read=lambda p:json.loads(p.read_text(encoding='utf8'))
rows=read(C/'inventory.json');base=[r for r in rows if int(r['key'])<337]
mount=cq.Shape.importBrep(str(C/'318.brep'));body=cq.Shape.importBrep(str(G/'69.brep'))
def bores(s):
 points=[]
 for f in s.Faces():
  a=BRepAdaptor_Surface(f.wrapped)
  if a.GetType()!=GeomAbs_Cylinder:continue
  c=a.Cylinder();d=c.Axis().Direction();p=c.Axis().Location()
  if abs(c.Radius()-1.7)<1e-5 and abs(d.Z())>.999:points.append((p.X(),p.Y()))
 assert len(points)==2
 return sorted(points)
a,b=bores(mount),bores(body);dx=sum(x[0]for x in a)/2-sum(x[0]for x in b)/2;dy=sum(x[1]for x in a)/2-sum(x[1]for x in b)/2
dz=mount.BoundingBox().zmax-body.BoundingBox().zmin;translation=(dx,dy,dz)
error=max(abs(a[i][j]-b[i][j]-translation[j])for i in range(2)for j in range(2));assert error<.0001,error
selected=list(range(59));selected.remove(5);selected.remove(6);selected +=[68,69,71,72,73]
mapping={};pairs=[]
for i,k in enumerate(selected,337):
 src=next(r for r in read(G/'inventory.json')if r['key']==str(k));s=cq.Shape.importBrep(str(G/(str(k)+'.brep'))).translate(translation);s.exportBrep(str(C/(str(i)+'.brep')));bb=s.BoundingBox()
 r={**src,'key':str(i),'path':['Toolhead <1>','Galileo 2 G2SA',*src['path'][2:]],'source_key':str(k),'source_component':'galileo2_g2sa','bounds_mm':[[bb.xmin,bb.ymin,bb.zmin],[bb.xmax,bb.ymax,bb.zmax]],'valid':s.isValid(),'volume_mm3':s.Volume()};base.append(r);mapping[str(k)]=str(i)
 for j in [318,319,325,326,327,328,331,332,336]:
  t=cq.Shape.importBrep(str(C/(str(j)+'.brep')));tb=t.BoundingBox()
  overlap=bb.xmin<=tb.xmax and bb.xmax>=tb.xmin and bb.ymin<=tb.ymax and bb.ymax>=tb.ymin and bb.zmin<=tb.zmax and bb.zmax>=tb.zmin
  if overlap:
   common=s.intersect(t).Volume();distance=s.distance(t);pairs.append(dict(g2sa=k,rook=j,distance_mm=distance,common_mm3=common));assert common<.05,(k,j,common)
report=dict(display_registration_passed=True,translation_mm=translation,hole_pitch_mm=a[1][0]-a[0][0],maximum_bore_axis_error_mm=error,source_sha256=read(G/'SOURCE.json')['sha256'],source_commit=read(G/'SOURCE.json')['commit'],parts=mapping,selected_native_solid_pairs=pairs,scope='Upright Sherpa-foot G2SA on the original Rook MK2 mount: two analytic M3 bore axes, exact planar seating and selected native-solid intersections. Rook CAD does not supply the two foot mounting screws or clamping receivers; these are not invented. This display registration is not complete fastening or swept clearance certification.')
(C/'inventory.json').write_text(json.dumps(base,ensure_ascii=False,indent=2)+'\n',encoding='utf8');(C/'G2SA_REGISTRATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
