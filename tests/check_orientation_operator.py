"""Run with Blender --background --factory-startup; disposable session only."""
from pathlib import Path
import types, math
import bpy, bmesh
root=Path(__file__).resolve().parents[1]
addon=types.ModuleType('orientation_checks')
exec(compile((root/'__init__.py').read_text(),str(root/'__init__.py'),'exec'),addon.__dict__)
class Reports:
    def __init__(self): self.messages=[]
    def report(self,level,message): self.messages.append((level,message))
mesh=bpy.data.meshes.new('OrientationCheck')
coords=[]; faces=[]
for i in range(3):
    k=len(coords); coords.extend([(i*3,0,0),(i*3+1,0,0),(i*3+1,1,0),(i*3,1,0)])
    faces.append(tuple(range(k,k+4)))
mesh.from_pydata(coords,[],faces); mesh.uv_layers.new()
obj=bpy.data.objects.new('OrientationCheck',mesh); bpy.context.collection.objects.link(obj)
for o in bpy.context.selected_objects: o.select_set(False)
obj.select_set(True); bpy.context.view_layer.objects.active=obj
bpy.context.tool_settings.use_uv_select_sync=True
bpy.ops.object.mode_set(mode='EDIT')
bm=bmesh.from_edit_mesh(mesh); bm.faces.ensure_lookup_table(); uv=bm.loops.layers.uv.active
for i,face in enumerate(bm.faces):
    face.select_set(True)
    for l,(x,y) in zip(face.loops,[(0,0),(1,0),(1,1),(0,1)]):
        l[uv].uv=((x*math.cos(.4)-y*math.sin(.4), x*math.sin(.4)+y*math.cos(.4)) if i==0 else ((x,y) if i==1 else (-x,y)))
bmesh.update_edit_mesh(mesh)
r=Reports(); assert addon.CS2WD_OT_WorldOrient.execute(r,bpy.context)=={'FINISHED'}
assert 'Rotated 1 island(s); 1 already aligned; skipped 1' in r.messages[-1][1],r.messages
r=Reports(); assert addon.CS2WD_OT_WorldOrient.execute(r,bpy.context)=={'FINISHED'}
assert 'Rotated 0 island(s); 2 already aligned; skipped 1' in r.messages[-1][1],r.messages
for f in bm.faces: f.select_set(f.index==2)
r=Reports(); assert addon.CS2WD_OT_WorldOrient.execute(r,bpy.context)=={'CANCELLED'}
assert 'ambiguous orientation' in r.messages[-1][1]
for f in bm.faces: f.select_set(False)
r=Reports(); assert addon.CS2WD_OT_WorldOrient.execute(r,bpy.context)=={'CANCELLED'}
assert r.messages[-1][1]=='No UV islands selected'
obj.scale.y=0
bpy.context.view_layer.update()
r=Reports(); assert addon.CS2WD_OT_WorldOrient.execute(r,bpy.context)=={'CANCELLED'}
assert 'zero scale' in r.messages[-1][1]
obj.scale.y=1
bpy.context.view_layer.update()
for f in bm.faces: f.select_set(f.index==0)
for l in bm.faces[0].loops:
    x,y=l[uv].uv
    l[uv].uv=(x*math.cos(.3)-y*math.sin(.3),x*math.sin(.3)+y*math.cos(.3))
bmesh.update_edit_mesh(mesh)
bpy.utils.register_class(addon.CS2WD_OT_WorldOrient)
before=[tuple(l[uv].uv) for l in bm.faces[0].loops]
bpy.ops.ed.undo_push(message='Before orientation check')
assert bpy.ops.cs2wd.world_orient()=={'FINISHED'}
bpy.ops.ed.undo_push(message='After orientation check')
assert bpy.ops.ed.undo()=={'FINISHED'}
bm=bmesh.from_edit_mesh(bpy.context.object.data); bm.faces.ensure_lookup_table(); uv=bm.loops.layers.uv.active
after=[tuple(l[uv].uv) for l in bm.faces[0].loops]
assert all(abs(a-b)<1e-6 for x,y in zip(before,after) for a,b in zip(x,y)),(before,after)
print('MW_ORIENTATION_OPERATOR_PASS: mixed counts, repeated run, all-skipped cancellation, no selection, zero scale, registration and UV undo')
