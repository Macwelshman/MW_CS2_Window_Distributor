"""Focused circular-angle and UV-outcome checks using disposable BMeshes."""
import math
import bmesh
from mathutils import Matrix

def run_orientation_checks(addon):
    checks = []
    angle,reason = addon._weighted_orientation_angle([(math.radians(179),1),(math.radians(-179),1)])
    assert reason is None and abs(abs(angle)-math.pi)<1e-6
    samples=[(.4,1.2),(-2.8,.3),(2.9,.7),(.01,2)]
    first=addon._weighted_orientation_angle(samples)
    assert addon._weighted_orientation_angle(list(reversed(samples))) == first
    assert addon._weighted_orientation_angle([(0,1),(math.pi,1)])[1] == 'ambiguous orientation'
    assert addon._weighted_orientation_angle([])[1] == 'no usable edges'
    checks.append('angle wraparound, reversed input, cancellation and empty input')
    for rotation, expected in [(0,'ALIGNED'),(.47,'ROTATED'),(math.pi-1e-4,'ROTATED'),(-math.pi+1e-4,'ROTATED')]:
        bm=bmesh.new()
        try:
            verts=[bm.verts.new(p) for p in [(0,0,0),(2,0,0),(2,1,0),(0,1,0)]]
            face=bm.faces.new(verts); bm.normal_update(); bm.faces.index_update()
            uv=bm.loops.layers.uv.new()
            for l in face.loops:
                x,y=l.vert.co.xy
                l[uv].uv=(x*math.cos(rotation)-y*math.sin(rotation),x*math.sin(rotation)+y*math.cos(rotation))
            before=[l[uv].uv.copy() for l in face.loops]
            outcome=addon._world_orient_island([face],uv,Matrix.Identity(4),Matrix.Identity(3))
            assert outcome == (expected,None),outcome
            after=[l[uv].uv.copy() for l in face.loops]
            for i in range(4):
                for j in range(i):
                    assert abs((before[i]-before[j]).length-(after[i]-after[j]).length)<2e-5
            assert addon._world_orient_island([face],uv,Matrix.Identity(4),Matrix.Identity(3)) == ('ALIGNED',None)
            assert all((l[uv].uv-a).length==0 for l,a in zip(face.loops,after))
            for l in face.loops: l[uv].uv=(0,0)
            assert addon._world_orient_island([face],uv,Matrix.Identity(4),Matrix.Identity(3)) == ('SKIPPED','no usable edges')
        finally: bm.free()
    checks.append('rotated/aligned/skipped results, preserved UV distances and unchanged second execution')
    bm=bmesh.new()
    try:
        v=[bm.verts.new(p) for p in [(0,0,0),(1,0,0),(1,1,0),(0,1,0)]]
        f=bm.faces.new(v); bm.normal_update(); uv=bm.loops.layers.uv.new()
        for l in f.loops: l[uv].uv=(-l.vert.co.x,l.vert.co.y)
        before=[tuple(l[uv].uv) for l in f.loops]
        assert addon._world_orient_island([f],uv,Matrix.Identity(4),Matrix.Identity(3)) == ('SKIPPED','ambiguous orientation')
        assert [tuple(l[uv].uv) for l in f.loops] == before
    finally: bm.free()
    checks.append('ambiguous mirrored square skipped without UV changes')
    return checks
