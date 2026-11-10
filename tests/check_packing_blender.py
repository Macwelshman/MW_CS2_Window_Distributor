"""blender --background --factory-startup --python-exit-code 1 --python tests/check_packing_blender.py"""
from pathlib import Path
import types
import bpy
import bmesh
root = Path(__file__).resolve().parents[1]
addon = types.ModuleType('packing_checks')
exec(compile((root/'__init__.py').read_text(), str(root/'__init__.py'), 'exec'), addon.__dict__)
for name, function in (('check_distribution_reliability','run_checks'),
                       ('check_uv_edit_context','run_checks'),
                       ('check_orientation','run_orientation_checks'),
                       ('check_world_normals','run_checks')):
    ns = {'__file__': str(root/'tests'/f'{name}.py')}
    exec(compile((root/'tests'/f'{name}.py').read_text(), name, 'exec'), ns)
    print(name, ns[function](addon))
# Existing registered-operator selection/preset integration tests.
ns = {'__file__': str(root/'tests/check_distribution_selection.py')}
exec(compile((root/'tests/check_distribution_selection.py').read_text(), 'selection', 'exec'), ns)
# Capture native multi-object Edit Mode UVs, pack, and restore through Undo.
if bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
objects = [bpy.context.object]
mesh = objects[0].data.copy()
obj = bpy.data.objects.new('UndoSecond', mesh)
bpy.context.collection.objects.link(obj); obj.select_set(True); objects.append(obj)
bpy.ops.object.mode_set(mode='EDIT')
bpy.context.tool_settings.use_uv_select_sync = True
for obj in objects:
    bm = bmesh.from_edit_mesh(obj.data)
    for face in bm.faces: face.select_set(True)
    bmesh.update_edit_mesh(obj.data)
def state():
    result = []
    for name in sorted(o.name for o in objects):
        bm = bmesh.from_edit_mesh(bpy.data.objects[name].data)
        uv = bm.loops.layers.uv.active
        result.append(tuple(tuple(loop[uv].uv) for face in bm.faces for loop in face.loops))
    return result
props = bpy.context.scene.cs2wd_props
assert props.padding_units == 'UV'
props.tile_padding = .01; props.island_padding = .001
props.padding_units = 'PIXELS'
props.atlas_resolution = '2048'
props.tile_padding_px = props.island_padding_px = 4
assert addon._effective_padding(props) == (4 / 2048, 4 / 2048)
props.padding_units = 'UV'
assert abs(addon._effective_padding(props)[0] - .01) < 1e-8
props.padding_units = 'PIXELS'
before = state()
bpy.ops.ed.undo_push(message='Before packing')
assert bpy.ops.cs2wd.distribute_uv() == {'FINISHED'}
assert state() != before
bpy.ops.ed.undo_push(message='After packing')
assert bpy.ops.ed.undo() == {'FINISHED'}
# Undo invalidates object references; recover names from the view layer.
objects = [o for o in bpy.context.objects_in_mode_unique_data if o.type == 'MESH']
assert state() == before
print('PACKING_UNDO_PASS: native multi-object distribution restores UVs')
