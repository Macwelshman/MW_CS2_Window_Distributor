"""Run through Flue in a disposable factory-startup Blender session."""
import math
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
    result = {}
    for name in names:
        bm = bmesh.from_edit_mesh(bpy.data.objects[name].data)
        uv = bm.loops.layers.uv.active
        result[name] = tuple(tuple(loop[uv].uv) for face in bm.faces for loop in face.loops)
    return result
names = {obj.name for obj in objects}
props = bpy.context.scene.cs2wd_props
assert props.padding_units == 'UV'
assert math.isclose(props.tile_padding_percent, 1.0, abs_tol=1e-6)
assert math.isclose(addon._effective_padding(props)[0], .002, abs_tol=1e-8)
assert math.isclose(props.island_padding_percent, .5, abs_tol=1e-6)
assert props.tile_padding_px == 4
props.tile_padding = 0
assert props.tile_padding_percent == 0  # An explicitly saved zero still means zero.
props.tile_padding = .01; props.island_padding = .001
assert math.isclose(props.tile_padding_percent, 5, abs_tol=1e-6)
props.tile_padding_percent = 1.25
props.island_padding_percent = .75
assert all(math.isclose(actual, expected, abs_tol=1e-8)
           for actual, expected in zip(addon._effective_padding(props), (.0025, .0015)))
props.padding_units = 'PIXELS'
props.atlas_resolution = '2048'
props.tile_padding_px = props.island_padding_px = 4
assert addon._effective_padding(props) == (4 / 2048, 4 / 2048)
props.padding_units = 'UV'
assert math.isclose(props.tile_padding_percent, 1.25, abs_tol=1e-6)
assert math.isclose(props.island_padding_percent, .75, abs_tol=1e-6)
print('PADDING_PERCENT_PASS: defaults, saved UV values, percent edits and independent pixel settings')
before = state()
assert len(names) == 2
assert bpy.ops.ed.undo_push(message='Before packing') == {'FINISHED'}
assert bpy.ops.cs2wd.distribute_uv('EXEC_DEFAULT', True) == {'FINISHED'}
after = state()
assert all(after[name] != before[name] for name in names)
assert bpy.ops.ed.undo() == {'FINISHED'}
assert {o.name for o in bpy.context.objects_in_mode_unique_data if o.type == 'MESH'} == names
assert state() == before, 'Undo must exactly restore every UV on both meshes'
print('PACKING_UNDO_PASS: native multi-object distribution restores UVs')
