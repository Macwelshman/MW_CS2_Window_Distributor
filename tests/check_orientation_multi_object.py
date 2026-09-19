"""Run in a disposable Blender --background --factory-startup session."""
from pathlib import Path
import math
import types
import bpy
import bmesh

root = Path(__file__).resolve().parents[1]
addon = types.ModuleType('multi_orientation_checks')
exec(compile((root / '__init__.py').read_text(), str(root / '__init__.py'), 'exec'), addon.__dict__)
bpy.utils.register_class(addon.CS2WD_OT_WorldOrient)


def snapshot(objects):
    result = []
    for obj in objects:
        bm = bmesh.from_edit_mesh(obj.data)
        uv = bm.loops.layers.uv.active
        result.append([tuple(lp[uv].uv) for f in bm.faces for lp in f.loops])
    return result


for sync in (True, False):
    for active_index in (0, 1):
        if bpy.context.object and bpy.context.object.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        bpy.context.tool_settings.use_uv_select_sync = sync
        objects = []
        for i in range(3):
            mesh = bpy.data.meshes.new(f'MultiMesh{i}')
            mesh.from_pydata([(0,0,0),(2,0,0),(2,1,0),(0,1,0)], [], [(0,1,2,3)])
            mesh.uv_layers.new()
            # Third object's UVs are not selected, although its mesh is visible.
            for name, domain, size in [('.uv_select_vert','CORNER',4),('.uv_select_face','FACE',1),('.uv_select_edge','CORNER',4)]:
                attr = mesh.attributes.get(name) or mesh.attributes.new(name, 'BOOLEAN', domain)
                for item in attr.data:
                    item.value = i < 2
            for poly in mesh.polygons:
                poly.select = i < 2 if sync else True
            for lp, (x,y) in zip(mesh.uv_layers.active.data, [(0,0),(2,0),(2,1),(0,1)]):
                lp.uv = (x*math.cos(.6)-y*math.sin(.6), x*math.sin(.6)+y*math.cos(.6))
            obj = bpy.data.objects.new(f'MultiObject{i}', mesh)
            bpy.context.collection.objects.link(obj)
            obj.select_set(True)
            obj.rotation_euler.z = .2 * i
            obj.scale = (1+i*.3, 1, 1)
            objects.append(obj)
        bpy.context.view_layer.objects.active = objects[active_index]
        bpy.context.tool_settings.use_uv_select_sync = sync
        bpy.context.view_layer.update()
        bpy.ops.object.mode_set(mode='EDIT')
        if sync:
            for i, obj in enumerate(objects):
                bm = bmesh.from_edit_mesh(obj.data)
                for face in bm.faces:
                    face.select_set(i < 2)
                bmesh.update_edit_mesh(obj.data)
        before = snapshot(objects)
        bpy.ops.ed.undo_push(message='Before multi orientation')
        assert bpy.ops.cs2wd.world_orient() == {'FINISHED'}
        after = snapshot(objects)
        assert all(after[i] != before[i] for i in (0,1)), (sync, active_index)
        assert after[2] == before[2], 'Unselected UVs changed'
        assert bpy.context.view_layer.objects.active == objects[active_index]
        assert all(obj.mode == 'EDIT' for obj in objects)
        for i in (0,1):
            bm = bmesh.from_edit_mesh(objects[i].data)
            uv = bm.loops.layers.uv.active
            faces = list(bm.faces)
            assert addon._world_orient_island(faces, uv, objects[i].matrix_world, addon._world_normal_transform(objects[i].matrix_world)) == ('ALIGNED', None)
        assert bpy.ops.cs2wd.world_orient() == {'FINISHED'}
        assert snapshot(objects) == after
        names = [obj.name for obj in objects]
        bpy.ops.ed.undo_push(message='After multi orientation')
        assert bpy.ops.ed.undo() == {'FINISHED'}
        objects = [bpy.data.objects[name] for name in names]
        assert snapshot(objects) == before, 'Multi-object Undo did not restore UVs'
print('MW_MULTI_ORIENTATION_PASS: both active objects, UV sync on/off, transforms, unselected UVs, repeated run, Edit Mode and Undo')
