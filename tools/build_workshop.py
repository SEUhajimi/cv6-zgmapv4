# 生成创意工坊上传文件夹：python tools/build_workshop.py Han_LiuBei
# 只复制 .modinfo 和其 <Files> 里登记的文件到 dist/workshop/<mod>/，README、开发文件不会带上。
# workshop/<mod>/ 下的预览图和工坊介绍不进上传文件夹，上传时在 Mod Uploader 里单独选。
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIEW_LIMIT = 1024 * 1024  # Steam 预览图上限 1MB


def build(mod):
    src = ROOT / mod
    modinfos = list(src.glob('*.modinfo'))
    if len(modinfos) != 1:
        sys.exit(f'{src} 下应有且只有一个 .modinfo，找到 {len(modinfos)} 个')
    modinfo = modinfos[0]
    root = ET.parse(modinfo).getroot()
    files = [f.text.strip() for f in root.iterfind('Files/File')]
    missing = [f for f in files if not (src / f).is_file()]
    if missing:
        sys.exit('modinfo 登记了但不存在的文件：\n  ' + '\n  '.join(missing))

    out = ROOT / 'dist' / 'workshop' / mod
    if out.exists():
        shutil.rmtree(out)
    for rel in [modinfo.name] + files:
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, out / rel)

    listed = {modinfo.name, *(Path(f).as_posix() for f in files)}
    skipped = sorted(p.relative_to(src).as_posix() for p in src.rglob('*')
                     if p.is_file() and p.relative_to(src).as_posix() not in listed)
    print(f'{root.get("id")} v{root.get("version")}  {root.findtext("Properties/Name")}')
    print(f'已复制 {len(listed)} 个文件到 {out}')
    if skipped:
        print('未登记、没有复制：' + '、'.join(skipped))

    for preview in sorted((ROOT / 'workshop' / mod).glob('preview.*')):
        size = preview.stat().st_size
        flag = '' if size < PREVIEW_LIMIT else '  超过 1MB，Steam 会拒绝'
        print(f'预览图 {preview}（{size // 1024} KB）{flag}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('用法：python tools/build_workshop.py <mod 文件夹名>')
    build(sys.argv[1])
