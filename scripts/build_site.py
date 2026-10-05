"""Build the pinned native community printer web assets."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();target=a.output.resolve()
 if target.exists()or target.is_relative_to(ROOT/'site'):raise ValueError('Use a new build directory')
 source=ROOT/'site';index=json.loads((source/'ASSET_INDEX.json').read_text(encoding='utf-8'));expected={v['path']for v in index['files'].values()}|{'ASSET_INDEX.json','NOTICE.txt'}
 assert {f.relative_to(source).as_posix()for f in source.rglob('*')if f.is_file()}==expected
 total=0
 for r in index['files'].values():
  f=(source/r['path']).resolve();assert f.is_relative_to(source.resolve())and f.stat().st_size==r['bytes']
  with f.open('rb')as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==r['sha256']
  total+=r['bytes']
 assert total<900_000_000
 shutil.copytree(source,target);(target/'.nojekyll').touch();print(f'Built {len(expected)} community printer files ({total:,} model bytes).')
if __name__=='__main__':main()
