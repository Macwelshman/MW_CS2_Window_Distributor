"""Run in Blender with the add-on module supplied as `addon`; no scene edits."""
import bpy
import bmesh
from mathutils import Matrix, Vector

def run_checks(addon):
    checks = []
    allocated = []
    def mesh(points, polygons, uv=False):
        bm = bmesh.new(); allocated.append(bm)
        verts = [bm.verts.new(p) for p in points]
        for polygon in polygons:
            bm.faces.new([verts[i] for i in polygon])
        bm.normal_update()
        layer = bm.loops.layers.uv.new() if uv else None
        if uv:
            for face in bm.faces:
                for loop, coord in zip(face.loops, [(0,0),(2,0),(2,1),(0,1)]):
                    loop[layer].uv = coord
        return bm, layer
    def normal(bm, mat):
        return addon._island_world_normal(list(bm.faces), addon._world_normal_transform(mat))
    def close(a,b):
        assert (a-b).length < 2e-5, (tuple(a),tuple(b))
    try:
        bm,_ = mesh([(0,0,0),(2,0,1),(0,3,1)],[(0,1,2)])
        for scale in [(1,1,1),(3,.4,2),(-3,.4,2),(-3,-.4,2),(.001,.001,.001)]:
            mat = Matrix.Rotation(.43,4,'Z') @ Matrix.Diagonal((*scale,1))
            coords = [mat @ v.co for v in bm.verts]
            expected = (coords[1]-coords[0]).cross(coords[2]-coords[0]).normalized()
            close(normal(bm,mat), expected)
            applied,_ = mesh(coords,[(0,1,2)])
            close(normal(bm,mat),normal(applied,Matrix.Identity(4)))
        checks.append('rotated, nonuniform, mirrored, double-negative and small scale: geometric normals and applied equivalence')
        weighted,_ = mesh([(0,0,0),(4,0,0),(0,3,0),(0,0,0),(0,1,0),(0,0,1)],[(0,1,2),(3,4,5)])
        mat = Matrix.Diagonal((2,3,4,1))
        close(normal(weighted,mat),Vector((6,0,36)).normalized())
        checks.append('world-area weighting on unequal differently oriented faces')
        quad,_ = mesh([(0,0,0),(4,0,1),(4,2,1),(0,2,0)],[(0,1,2,3)])
        triangulated,_ = mesh([v.co.copy() for v in quad.verts],[(0,1,2),(0,2,3)])
        close(normal(quad,mat),normal(triangulated,mat))
        checks.append('planar triangulation invariance of normals')
        for scale in [(0,1,1),(1,0,1),(1,1,0)]:
            try: addon._world_normal_transform(Matrix.Diagonal((*scale,1)))
            except ValueError: pass
            else: raise AssertionError('zero scale accepted')
        collapsed,_ = mesh([(0,0,0),(1,0,0),(2,0,0)],[(0,1,2)])
        opposed,_ = mesh([(0,0,0),(1,0,0),(0,1,0),(0,0,1),(1,0,1),(0,1,1)],[(0,1,2),(5,4,3)])
        assert normal(collapsed,mat) is None
        assert normal(opposed,mat) is None
        assert addon._island_world_normal([],Matrix.Identity(3)) is None
        checks.append('zero scale rejected; empty, degenerate and cancelling normals skipped')
        for scale in [(1,1,1),(3,.4,2),(-3,.4,2)]:
            local,uv = mesh([(0,0,0),(2,0,1),(2,3,1),(0,3,0)],[(0,1,2,3)],True)
            mat = Matrix.Rotation(.31,4,'Z') @ Matrix.Diagonal((*scale,1))
            applied,av = mesh([mat@v.co for v in local.verts],[(0,1,2,3)],True)
            loops = list(next(iter(local.faces)).loops)
            before = [l[uv].uv.copy() for l in loops]
            assert addon._world_orient_island(list(local.faces),uv,mat,addon._world_normal_transform(mat))[0] in {"ROTATED", "ALIGNED"}
            assert addon._world_orient_island(list(applied.faces),av,Matrix.Identity(4),Matrix.Identity(3))[0] in {"ROTATED", "ALIGNED"}
            after = [l[uv].uv.copy() for l in loops]
            other = [l[av].uv.copy() for l in next(iter(applied.faces)).loops]
            for a,b in zip(after,other): close(a,b)
            for i in range(4):
                for j in range(i):
                    assert abs((before[i]-before[j]).length-(after[i]-after[j]).length)<2e-5
        checks.append('UV orientation applied/unapplied equivalence and all pairwise UV distances preserved')
        return {'version': bpy.app.version_string, 'passed': checks}
    finally:
        for bm in allocated: bm.free()
