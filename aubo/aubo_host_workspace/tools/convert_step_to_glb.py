import argparse
import os
import tempfile

import trimesh
import gmsh


def convert_step_to_glb(step_path: str, glb_path: str, linear_deflection: float = 0.8, angular_deflection: float = 0.3) -> None:
    step_path = os.path.abspath(step_path)
    glb_path = os.path.abspath(glb_path)
    os.makedirs(os.path.dirname(glb_path), exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tf:
        stl_path = tf.name

    # 方案1：gmsh（快，依赖少）
    gmsh_ok = False
    try:
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.open(step_path)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMin", linear_deflection)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", linear_deflection * 2.0)
        gmsh.option.setNumber("Mesh.AngleToleranceFacetOverlap", angular_deflection)
        gmsh.model.mesh.generate(2)
        gmsh.write(stl_path)
        gmsh_ok = os.path.exists(stl_path) and os.path.getsize(stl_path) > 0
    except Exception:
        gmsh_ok = False
    finally:
        try:
            gmsh.finalize()
        except Exception:
            pass

    # 方案2：cadquery（gmsh 不稳定时兜底）
    if not gmsh_ok:
        try:
            import cadquery as cq
            from cadquery import exporters
        except Exception as exc:
            raise RuntimeError("STEP 转换失败：gmsh 与 cadquery 均不可用") from exc
        model = cq.importers.importStep(step_path)
        exporters.export(model, stl_path, tolerance=linear_deflection, angularTolerance=angular_deflection)

    try:
        mesh = trimesh.load(stl_path, force="mesh", process=False)
        if not isinstance(mesh, trimesh.Trimesh):
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        mesh.export(glb_path)
    finally:
        if os.path.exists(stl_path):
            os.remove(stl_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert STEP to GLB using gmsh+trimesh")
    parser.add_argument("--step", required=True, help="Input STEP path")
    parser.add_argument("--glb", required=True, help="Output GLB path")
    parser.add_argument("--linear", type=float, default=0.8, help="Linear deflection-ish mesh size")
    parser.add_argument("--angular", type=float, default=0.3, help="Angular tolerance")
    args = parser.parse_args()

    convert_step_to_glb(args.step, args.glb, args.linear, args.angular)
    print(f"Converted: {args.step} -> {args.glb}")


if __name__ == "__main__":
    main()
