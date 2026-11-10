"""Native edit-mesh integration in an isolated scene and view layer via Flue.

No registration or installed add-on replacement. Caller supplies source module.
"""
import bpy
import bmesh
import types


def run_checks(addon):
    original_scene = bpy.context.scene
    original_active = bpy.context.view_layer.objects.active
    original_mode = bpy.context.mode
    scene = bpy.data.scenes.new('MW_Disposable_UV_Check')
    objects=[]
    meshes=[]
    reports=[]
    class Props(types.SimpleNamespace):
        validate_window_selection=addon.CS2WDProperties.validate_window_selection
        get_selected_tiles=addon.CS2WDProperties.get_selected_tiles
    props=Props(mode='residential',curtains=True,curtains_closed=False,use_specific_tiles=False,
                exclude_edges=True,padding_units='UV', tile_padding=0.,island_padding=.001,
                allow_upscale=True,randomize_distribution=False,random_seed=0)
    op=types.SimpleNamespace(report=lambda level,msg:reports.append(msg))
    op._collect_island_data=addon.CS2WD_OT_DistributeUV._collect_island_data.__get__(op)
    try:
        for n in range(2):
            mesh=bpy.data.meshes.new('MW_Check_Mesh'); meshes.append(mesh)
            mesh.from_pydata([(0,0,0),(2,0,0),(2,1,0),(0,1,0)],[],[(0,1,2,3)])
            mesh.uv_layers.new(name='Untouched'); mesh.uv_layers.new(name='Chosen')
            mesh.uv_layers.active_index=1
            for l,co in zip(mesh.uv_layers['Chosen'].data,[(0,0),(2,0),(2,1),(0,1)]): l.uv=co
            for l in mesh.uv_layers['Untouched'].data: l.uv=(7,8)
            obj=bpy.data.objects.new('MW_Check_Object',mesh); objects.append(obj); scene.collection.objects.link(obj)
        view=scene.view_layers[0]
        with bpy.context.temp_override(scene=scene,view_layer=view):
            for obj in objects: obj.select_set(True,view_layer=view)
            view.objects.active=objects[0]
            bpy.ops.object.mode_set(mode='EDIT')
            try:
                for obj in objects:
                    bm=bmesh.from_edit_mesh(obj.data)
                    for face in bm.faces: face.select_set(True); face.uv_select_set(True)
                    bmesh.update_edit_mesh(obj.data)
                context=types.SimpleNamespace(objects_in_mode_unique_data=objects,edit_object=objects[0],
                    scene=types.SimpleNamespace(cs2wd_props=props),tool_settings=scene.tool_settings,view_layer=view)
                def state():
                    result=[]
                    for obj in objects:
                        bm=bmesh.from_edit_mesh(obj.data)
                        result.append([(f.select,f.hide,f.uv_select,tuple((l.uv_select_vert,l.uv_select_edge) for l in f.loops)) for f in bm.faces])
                    return result
                for sync in (False,True):
                    scene.tool_settings.use_uv_select_sync=sync
                    for mode in (('VERTEX','EDGE','FACE') if sync else ('VERTEX','EDGE','FACE','ISLAND')):
                        scene.tool_settings.uv_select_mode='VERTEX' if mode=='ISLAND' else mode
                        scene.tool_settings.use_uv_select_island=mode=='ISLAND'
                        before=state()
                        assert addon.CS2WD_OT_DistributeUV.execute(op,context)=={'FINISHED'},reports
                        assert state()==before
                        assert view.objects.active==objects[0] and all(o.mode=='EDIT' for o in objects)
                        for obj in objects:
                            bm=bmesh.from_edit_mesh(obj.data); layer=bm.loops.layers.uv['Untouched']
                            assert all(tuple(l[layer].uv)==(7.,8.) for f in bm.faces for l in f.loops)
                        assert addon.CS2WD_OT_WorldOrient.execute(op,context)=={'FINISHED'},reports
                        assert state()==before
                return ['real multi-object Edit BMeshes, sync on/off, all UV modes, active map in both operators, selection/mode/active object preserved']
            finally:
                bpy.ops.object.mode_set(mode='OBJECT')
    finally:
        for obj in objects: bpy.data.objects.remove(obj,do_unlink=True)
        for mesh in meshes: bpy.data.meshes.remove(mesh)
        bpy.data.scenes.remove(scene)
        assert bpy.context.scene==original_scene
        assert bpy.context.view_layer.objects.active==original_active
        assert bpy.context.mode==original_mode
