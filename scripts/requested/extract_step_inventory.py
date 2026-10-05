"""Extract placed STEP leaves with names, colors and analytic BREP geometry."""
from pathlib import Path
import json,sys
import cadquery as cq
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.XCAFDoc import XCAFDoc_DocumentTool,XCAFDoc_ColorType
from OCP.TDF import TDF_LabelSequence,TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.Quantity import Quantity_Color
sys.stdout.reconfigure(encoding='utf8')
SRC=Path(sys.argv[1]);OUT=Path(sys.argv[2]);OUT.mkdir(parents=True,exist_ok=True)
doc=TDocStd_Document(TCollection_ExtendedString('XCAF'))
r=STEPCAFControl_Reader();r.SetNameMode(True);r.SetColorMode(True)
print('Reading',SRC.name,SRC.stat().st_size,flush=True);r.ReadFile(str(SRC));r.Transfer(doc)
st=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main());ct=XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
roots=TDF_LabelSequence();st.GetFreeShapes(roots);rows=[]
def name(label):
 a=TDataStd_Name()
 return a.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(),a) else ''
def walk(label,loc,parents):
 instance=label;nm=name(label)
 if st.IsReference_s(label):
  ref=TDF_Label();st.GetReferredShape_s(label,ref);loc=loc*cq.Location(st.GetLocation_s(label));label=ref
 path=parents+[nm or name(label)];children=TDF_LabelSequence();st.GetComponents_s(label,children)
 if children.Length():
  for i in range(1,children.Length()+1):walk(children.Value(i),loc,path)
  return
 s=cq.Shape(st.GetShape_s(label)).moved(loc)
 if s.wrapped.IsNull() or not s.Faces():return
 b=s.BoundingBox();rgb=None;c=Quantity_Color()
 for lab in [instance,label]:
  for typ in [XCAFDoc_ColorType.XCAFDoc_ColorSurf,XCAFDoc_ColorType.XCAFDoc_ColorGen]:
   if ct.GetColor_s(lab,typ,c):rgb=[c.Red(),c.Green(),c.Blue()];break
  if rgb:break
 key=str(len(rows));s.exportBrep(str(OUT/(key+'.brep')))
 rows.append(dict(key=key,name=name(label),path=path,bounds_mm=[[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]],
                  solids=len(s.Solids()),faces=len(s.Faces()),color=rgb,volume_mm3=s.Volume(),valid=s.isValid()))
 if len(rows)%100==0:print('Extracted',len(rows),flush=True)
for i in range(1,roots.Length()+1):walk(roots.Value(i),cq.Location(),[])
(OUT/'inventory.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
print('DONE',len(rows),'leaves; invalid',[p['key'] for p in rows if not p['valid']],flush=True)
