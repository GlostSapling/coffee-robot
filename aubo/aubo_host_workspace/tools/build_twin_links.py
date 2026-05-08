import os
from typing import List

import trimesh


def _group_index_by_z(z_mm: float) -> int:
    # Heuristic bands from base to TCP (unit: mm)
    if z_mm < 250:
        return 0
    if z_mm < 650:
        return 1
    if z_mm < 950:
        return 2
    if z_mm < 1250:
        return 3
    if z_mm < 1450:
        return 4
    if z_mm < 1580:
        return 5
    return 6


def build_links(src_glb: str, out_dir: str, min_faces: int = 12) -> List[str]:
    mesh = trimesh.load(src_glb, force="mesh", process=False)
    mesh.merge_vertices()
    parts = mesh.split(only_watertight=False)

    groups: List[List[trimesh.Trimesh]] = [[] for _ in range(7)]
    for p in parts:
        if len(p.faces) < min_faces:
            continue
        c = (p.bounds[0] + p.bounds[1]) / 2.0
        idx = _group_index_by_z(float(c[2]))
        groups[idx].append(p)

    os.makedirs(out_dir, exist_ok=True)
    outputs: List[str] = []
    for i, g in enumerate(groups):
        if not g:
            continue
        m = trimesh.util.concatenate(g) if len(g) > 1 else g[0]
        out = os.path.join(out_dir, f"link{i}.glb")
        m.export(out)
        outputs.append(out)
    return outputs


if __name__ == "__main__":
    src = r"d:\aubo\aubo_host_workspace\assets\i10H.glb"
    out = r"d:\aubo\aubo_host_workspace\assets\twin_links"
    files = build_links(src, out)
    print("generated:", len(files))
    for f in files:
        print(f)
