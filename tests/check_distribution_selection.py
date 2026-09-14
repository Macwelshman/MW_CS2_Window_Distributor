"""Run in a disposable Blender background session."""
from pathlib import Path
import types
import bpy
import bmesh
root = Path(__file__).resolve().parents[1]
addon = types.ModuleType('selection_checks')
exec(compile((root/'__init__.py').read_text(), 'addon', 'exec'), addon.__dict__)
addon.register()
mesh = bpy.data.meshes.new('SelectionCheck')
mesh.from_pydata([(0,0,0),(1,0,0),(2,0,0),(0,1,0),(1,1,0),(2,1,0)], [], [(0,1,4,3),(1,2,5,4)])
mesh.uv_layers.new()
for v in mesh.vertices: v.select = True
for e in mesh.edges: e.select = True
for p in mesh.polygons:
    p.select = True
    for i in p.loop_indices:
        co = mesh.vertices[mesh.loops[i].vertex_index].co
        mesh.uv_layers.active.data[i].uv = (co.x*.1, co.y*.1)
obj = bpy.data.objects.new('SelectionCheck', mesh)
bpy.context.collection.objects.link(obj)
for o in bpy.context.selected_objects: o.select_set(False)
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.context.tool_settings.use_uv_select_sync = False

def select_uv(indices):
    if obj.mode == 'EDIT': bpy.ops.object.mode_set(mode='OBJECT')
    attr = mesh.attributes.get('.uv_select_vert')
    if attr is None: attr = mesh.attributes.new('.uv_select_vert', 'BOOLEAN', 'CORNER')
    for p in mesh.polygons:
        for i in p.loop_indices: attr.data[i].value = p.index in indices
    for name, domain in [('.uv_select_face', 'FACE'), ('.uv_select_edge', 'CORNER')]:
        attr = mesh.attributes.get(name)
        if attr is None: attr = mesh.attributes.new(name, 'BOOLEAN', domain)
        for p in mesh.polygons:
            for i in ([p.index] if domain == 'FACE' else p.loop_indices):
                attr.data[i].value = p.index in indices
    bpy.ops.object.mode_set(mode='EDIT')

def coords():
    bm = bmesh.from_edit_mesh(mesh)
    uv = bm.loops.layers.uv.active
    return [tuple(tuple(l[uv].uv) for l in f.loops) for f in bm.faces]

props = bpy.context.scene.cs2wd_props
props.mode = 'residential'
props.curtains = True
select_uv({0,1})
assert bpy.ops.cs2wd.distribute_uv() == {'FINISHED'}
before = coords()
props.curtains = False
props.use_specific_tiles = True
select_uv({1})
assert bpy.ops.cs2wd.distribute_uv() == {'FINISHED'}
after = coords()
assert after[0] == before[0], 'Unselected connected face moved'
assert after[1] != before[1], 'Selected face did not move'
select_uv(set())
before = coords()
assert bpy.ops.cs2wd.distribute_uv() == {'CANCELLED'}
assert coords() == before
assert obj.mode == 'EDIT'
# Sync selection must also stop at the unselected adjacent face.
bpy.context.tool_settings.use_uv_select_sync = True
bm = bmesh.from_edit_mesh(mesh)
for f in bm.faces: f.select_set(f.index == 1)
before = coords()
assert bpy.ops.cs2wd.distribute_uv() == {'FINISHED'}
assert coords()[0] == before[0]
print('MW_DISTRIBUTION_SELECTION_PASS: curtains then selected blank, connected unselected UVs unchanged, empty selection cancels, edit mode restored, sync selection')
# Exact residential presets, including all Blank tiles, and combinations.
props.mode = 'residential'
expected = {
    'curtains': [3,9,11,15,17,23],
    'curtains_closed': [4,6,10,12,18,24],
    'use_specific_tiles': [1,2,5,7,8,13,14,16,19,20,21,22,25],
}
for key, numbers in expected.items():
    for option in expected: setattr(props, option, option == key)
    assert props.validate_window_selection()
    assert props.get_selected_tiles() == [n-1 for n in numbers]
    assert bpy.ops.cs2wd.distribute_uv() == {'FINISHED'}
for option in expected: setattr(props, option, True)
assert props.get_selected_tiles() == list(range(25))
assert props.bl_rna.properties['curtains'].name == 'Curtains (Open)'
assert props.bl_rna.properties['curtains_closed'].name == 'Curtains (Closed)'
# Residential Blank respects the shared exclusion control.
props.curtains = props.curtains_closed = False
props.exclude_edges = True
assert bpy.ops.cs2wd.distribute_uv() == {'FINISHED'}
uvs = coords()[1]
assert all(.2 <= x <= .4 and .8 <= y <= 1 for x,y in uvs), uvs
props.exclude_edges = False
assert bpy.ops.cs2wd.distribute_uv() == {'FINISHED'}
assert all(0 <= x <= .2 and .8 <= y <= 1 for x,y in coords()[1])
print('MW_RESIDENTIAL_PRESETS_PASS: exact tile sets, combinations, labels, operators, Blank exclusion on and off')
