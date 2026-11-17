"""Run run_checks(addon) in Blender; isolated BMeshes, no user scene changes.

The Edit Mesh adapter is substituted locally, while native BMesh UV/selection
and the actual operator implementations are exercised without registration.
"""
import math
import struct
import types
from mathutils import Matrix
import bmesh


def run_checks(addon):
    allocated = []
    updates = []
    class Props(types.SimpleNamespace):
        validate_window_selection = addon.CS2WDProperties.validate_window_selection
        get_selected_tiles = addon.CS2WDProperties.get_selected_tiles
    props = Props(mode='commercial', blinds_open=True, blinds_vertical=False,
                  blinds_closed=False, use_specific_tiles=False, curtains=False,
                  curtains_closed=False, exclude_edges=True, padding_units='UV', tile_padding=0.,
                  island_padding=.001, allow_upscale=True,
                  randomize_distribution=False, random_seed=17)
    class Obj:
        type = 'MESH'
        mode = 'EDIT'
        matrix_world = Matrix.Identity(4)
        def __init__(self, name, count, uv=True):
            self.name = name
            self.bm = bmesh.new(); allocated.append(self.bm)
            if uv:
                self.bm.loops.layers.uv.new('First')
                self.bm.loops.layers.uv.new('Active')
            for i in range(count):
                # Disconnected asymmetric quads, including a very narrow island.
                w, h = ((.002, .3) if i == 0 else (.12, .07))
                f = self.bm.faces.new([self.bm.verts.new(p) for p in
                    [(i,0,0),(i+1,0,0),(i+1,1,0),(i,1,0)]])
                f.select_set(True)
                if uv:
                    for l, co in zip(f.loops, [(i*.4,0),(i*.4+w,0),(i*.4+w,h),(i*.4,h)]):
                        l[self.bm.loops.layers.uv['Active']].uv = co
                        l[self.bm.loops.layers.uv['First']].uv = (8,9)
                    f.uv_select_set(True)
            self.bm.faces.index_update(); self.bm.normal_update()
            self.data = types.SimpleNamespace(uv_layers=types.SimpleNamespace(active=types.SimpleNamespace(name='Active') if uv else None), bm=self.bm)
    a, b, no_uv = Obj('A', 17), Obj('B', 14), Obj('NoUV', 1, False)
    context = types.SimpleNamespace(objects_in_mode_unique_data=[a,b,no_uv],
        edit_object=a, scene=types.SimpleNamespace(cs2wd_props=props),
        tool_settings=types.SimpleNamespace(use_uv_select_sync=False, uv_select_mode='VERTEX'),
        view_layer=types.SimpleNamespace(objects=types.SimpleNamespace(active=a)))
    reports = []
    op = types.SimpleNamespace(report=lambda level,msg: reports.append(msg))
    op._collect_island_data = addon.CS2WD_OT_DistributeUV._collect_island_data.__get__(op)
    def coords(obj, name='Active'):
        layer=obj.bm.loops.layers.uv.get(name)
        return tuple(tuple(tuple(l[layer].uv) for l in f.loops) for f in obj.bm.faces) if layer else ()
    def reset():
        for obj in (a,b):
            layer=obj.bm.loops.layers.uv['Active']
            for i,f in enumerate(obj.bm.faces):
                w,h=((.002,.3) if i==0 else (.12,.07))
                for l,co in zip(f.loops,[(i*.4,0),(i*.4+w,0),(i*.4+w,h),(i*.4,h)]): l[layer].uv=co
                f.select_set(True); f.uv_select_set(True)
    def run(): return addon.CS2WD_OT_DistributeUV.execute(op,context)
    # Substitute only the module's edit-mesh adapter; never patch global bmesh.
    original = addon.bmesh
    addon.bmesh = types.SimpleNamespace(from_edit_mesh=lambda data:data.bm,
        update_edit_mesh=lambda data:updates.append(data))
    checks=[]
    try:
        for mode in ('VERTEX','EDGE','FACE','ISLAND'):
            context.tool_settings.uv_select_mode=mode
            assert len(addon._snapshot_uv_face_selection(context,[a])[a])==17
            f=list(a.bm.faces)[0]; f.uv_select_set(False)
            assert 0 not in addon._snapshot_uv_face_selection(context,[a])[a]
            if mode in ('VERTEX','EDGE'):
                setter = f.loops[0].uv_select_vert_set if mode=='VERTEX' else f.loops[0].uv_select_edge_set
                setter(True)
                assert 0 not in addon._snapshot_uv_face_selection(context,[a])[a]
            f.uv_select_set(True)
        checks.append('native vertex/edge/face/island full and partial selection')
        for sync in (False,True):
            context.tool_settings.use_uv_select_sync=sync
            for seed in range(12):
                reset(); before=(coords(a),coords(b))
                props.randomize_distribution=True; props.random_seed=seed
                resolution = (512, 1024, 2048, 4096, 1500)[seed % 5]
                pixels = 0 if seed == 11 else 4
                props.padding_units = 'PIXELS' if seed else 'UV'
                props.atlas_resolution = 'CUSTOM' if resolution == 1500 else str(resolution)
                props.custom_resolution = resolution
                props.tile_padding_px = props.island_padding_px = pixels
                edge, gap = (pixels / resolution,) * 2 if seed else (0, .001)
                assert run()=={'FINISHED'}, reports[-1:]
                result=(coords(a),coords(b)); boxes={}; scales={}
                for old,new in zip(before[0]+before[1], result[0]+result[1]):
                    x=[p[0] for p in new]; y=[p[1] for p in new]
                    tile=(int((min(x)+max(x))/2*5),int((1-(min(y)+max(y))/2)*5))
                    index=tile[1]*5+tile[0]
                    assert index in set(props.get_selected_tiles())-{0,24}
                    lo_x,lo_y=tile[0]*.2,1-(tile[1]+1)*.2
                    assert min(x)>=lo_x+edge-1e-6 and max(x)<=lo_x+.2-edge+1e-6
                    assert min(y)>=lo_y+edge-1e-6 and max(y)<=lo_y+.2-edge+1e-6
                    sx=(max(x)-min(x))/(max(p[0] for p in old)-min(p[0] for p in old))
                    sy=(max(y)-min(y))/(max(p[1] for p in old)-min(p[1] for p in old))
                    assert abs(sx-sy)<2e-4
                    if index in scales: assert abs(sx-scales[index])<2e-4
                    scales[index]=sx
                    box=(min(x),max(x),min(y),max(y))
                    for other in boxes.setdefault(index,[]):
                        assert (box[0]>=other[1]+gap-1e-6 or other[0]>=box[1]+gap-1e-6 or
                                box[2]>=other[3]+gap-1e-6 or other[2]>=box[3]+gap-1e-6)
                    boxes[index].append(box)
                reset(); assert run()=={'FINISHED'}, reports[-1:]; assert (coords(a),coords(b))==result
                assert all(p==(8.,9.) for obj in (a,b) for face in coords(obj,'First') for p in face)
        props.padding_units = 'PIXELS'
        props.atlas_resolution = 'CUSTOM'
        props.custom_resolution = 1000
        props.island_padding_px = 0
        for pixels, expected in ((99, {'FINISHED'}), (100, {'CANCELLED'}), (101, {'CANCELLED'})):
            reset(); props.tile_padding_px = pixels
            before = (coords(a), coords(b)); updates.clear()
            assert run() == expected, reports[-1:]
            if expected == {'CANCELLED'}:
                assert (coords(a), coords(b)) == before and not updates
        props.padding_units = 'UV'
        checks.append('24 seeded multi-object packs: containment, exclusion, padding, overlap, aspect, repeatability, active map')
        # Exact reported Blank-only cases. Four per tile fits in two rows.
        # With 0.05 gaps there are at most 16 gap-sized centre cells per tile,
        # even if the islands are arranged without shelves.
        saved_objects = context.objects_in_mode_unique_data
        for count, expected in ((24, {'FINISHED'}), (216, {'CANCELLED'})):
            obj = Obj('Reported', count)
            context.objects_in_mode_unique_data = [obj]
            context.edit_object = obj
            props.blinds_open = False; props.use_specific_tiles = True
            props.tile_padding = .05 if count == 24 else 0
            props.island_padding = .05
            before = coords(obj); updates.clear()
            assert run() == expected, reports[-1:]
            if count == 216:
                assert coords(obj) == before and not updates
                assert 'Insufficient tile space in tile 2' in reports[-1]
                assert '36 islands; Tile Padding 0 UV, Island Padding 0.05 UV' in reports[-1]
                assert 'required gaps alone' in reports[-1]
            else:
                boxes = {}
                for face in coords(obj):
                    xs, ys = zip(*face)
                    ti = int((1-(min(ys)+max(ys))/2)*5)*5 + int((min(xs)+max(xs))/2*5)
                    tx, ty = (ti%5)*.2, 1-(ti//5+1)*.2
                    box = (min(xs), min(ys), max(xs), max(ys))
                    assert box[0]>=tx+.05-1e-6 and box[2]<=tx+.15+1e-6
                    assert box[1]>=ty+.05-1e-6 and box[3]<=ty+.15+1e-6
                    for other in boxes.setdefault(ti, []):
                        assert any(box[k]>=other[k+2]+.05-1e-6 or other[k]>=box[k+2]+.05-1e-6 for k in (0,1))
                    boxes[ti].append(box)
        early, late = Obj('Early', 1), Obj('Late', 1)
        context.objects_in_mode_unique_data = [early, late]
        context.edit_object = early
        props.tile_padding = props.island_padding = 0
        for obj in (early, late):
            layer = obj.bm.loops.layers.uv['Active']
            for loop, co in zip(next(iter(obj.bm.faces)).loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
                loop[layer].uv = co
        assert run() == {'FINISHED'}, reports[-1]
        # Tile 2 ends at 0.4; its nearest float32 rounds outside the tile.
        assert max(x for x, _ in coords(early)[0]) <= 2 / 5
        assert min(x for x, _ in coords(early)[0]) >= 1 / 5
        early_layer = early.bm.loops.layers.uv['Active']
        for loop in next(iter(early.bm.faces)).loops:
            loop[early_layer].uv.x += 2  # A partial commit would visibly move these UVs.
        late_loops = next(iter(late.bm.faces)).loops
        late_layer = late.bm.loops.layers.uv['Active']
        def uv_bytes(obj):
            return b''.join(struct.pack('ff', *co) for face in coords(obj) for co in face)
        for height, reason in ((1e-10, 'collapse'), (math.nan, 'non-finite source UVs')):
            # Keep both extents positive (the NaN is in the final corner),
            # so this exercises validation after the earlier tile is planned.
            for loop, co in zip(late_loops, [(0, 0), (1, 0), (1, 1e-10), (0, height)]):
                loop[late_layer].uv = co
            before = (uv_bytes(early), uv_bytes(late)); updates.clear()
            assert run() == {'CANCELLED'}, reports[-1]
            assert (uv_bytes(early), uv_bytes(late)) == before and not updates
            assert 'Insufficient tile space in tile 8' in reports[-1]
            assert 'Allow Upscale on' in reports[-1] and reason in reports[-1]
        context.objects_in_mode_unique_data = saved_objects; context.edit_object = a
        props.blinds_open = True; props.use_specific_tiles = False
        checks.append('exact Blank repros, strict tile edge, and atomic later-tile precision/non-finite failures')
        # Crowded tiles must fail before any changes.
        for tp,ip in ((.05,.1),(0,.2),(.05,.15)):
            reset(); props.tile_padding=tp; props.island_padding=ip
            before=(coords(a),coords(b)); updates.clear()
            assert run()=={'CANCELLED'}; assert (coords(a),coords(b))==before; assert not updates
        props.tile_padding=0; props.island_padding=.001
        # Reject an island with zero extent.
        reset(); props.randomize_distribution=False
        last=list(b.bm.faces)[-1]; layer=b.bm.loops.layers.uv['Active']
        for loop in last.loops: loop[layer].uv=(100,100)
        before=(coords(a),coords(b)); updates.clear()
        assert run()=={'CANCELLED'}; assert (coords(a),coords(b))==before; assert not updates
        reset(); props.randomize_distribution=False
        data=[]
        for obj in (a,b): data.extend(op._collect_island_data(obj,True)[0])
        data.sort(key=lambda d:(d['obj'].name,d['min'].y,d['min'].x))
        assert run()=={'FINISHED'},reports
        tile_indices=[i for i in props.get_selected_tiles() if i not in (0,24)]
        for ti in range(len(tile_indices)):
            assigned=data[ti::len(tile_indices)]
            index=tile_indices[ti]
            edge=(index%5)*.2+props.tile_padding
            left=edge
            top=1-(index//5)*.2-props.tile_padding
            bottom=top
            for j,d in enumerate(assigned):
                points=[uv.uv for uv in d['uvs']]
                actual_top=max(v.y for v in points)
                if j and abs(actual_top-top)>1e-6:
                    left, top = edge, bottom-props.island_padding
                    bottom=top
                assert abs(min(v.x for v in points)-left)<1e-6
                assert abs(actual_top-top)<1e-6
                left=max(v.x for v in points)+props.island_padding
                bottom=min(bottom,min(v.y for v in points))
        reset(); props.allow_upscale=False
        before=(coords(a),coords(b)); assert run()=={'FINISHED'},reports
        for old,new in zip(before[0]+before[1],coords(a)+coords(b)):
            assert math.dist(new[0],new[1]) <= math.dist(old[0],old[1])+1e-6
        # Selected-only distribution leaves even a full unselected island unchanged.
        f=list(a.bm.faces)[0]; f.select_set(False); before=coords(a)[0]
        assert run()=={'FINISHED'},reports; assert coords(a)[0]==before
        reset()
        for mode in ('commercial','residential'):
            props.mode=mode; props.blinds_open=False
            assert not props.get_selected_tiles(); assert run()=={'CANCELLED'}
        props.mode='commercial'; props.blinds_open=True
        context.objects_in_mode_unique_data=[no_uv]; context.edit_object=no_uv
        assert run()=={'CANCELLED'}; assert no_uv.bm.loops.layers.uv.active is None
        checks.append('padding failure atomicity, empty categories in both modes, no silent UV creation')
        return checks
    finally:
        addon.bmesh=original
        for bm in allocated: bm.free()
