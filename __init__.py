bl_info = {
    "name": "MW CS2 Window Distributor",
    "author": "Macwelshman",
    "version": (2, 7, 8),
    "blender": (5, 2, 0),
    "location": "UV Editor > Sidebar",
    "description": "Distribute windows across the CS2 window space.",
    "category": "UV",
}

import bpy
import bmesh
import random
import struct
from fractions import Fraction
from mathutils import Vector
import math

from math import sin, cos, atan2

DEBUG_TILE_SCALES = False
UV_EPSILON = 1e-6
TILE_PERCENT_UV = 0.2 / 100

# Residential mode tile sets (0-based indices)
RESI_CUR_TILES = [2, 8, 10, 14, 16, 22]
RESI_CUR_CLOSED_TILES = [3, 5, 9, 11, 17, 23]
RESI_BLANK_TILES = [0, 1, 4, 6, 7, 12, 13, 15, 18, 19, 20, 21, 24]

def _effective_padding(props):
    if props.padding_units == 'UV':
        return props.tile_padding, props.island_padding
    resolution = (props.custom_resolution if props.atlas_resolution == 'CUSTOM'
                  else int(props.atlas_resolution))
    return props.tile_padding_px / resolution, props.island_padding_px / resolution


def _validate_padding(tile_w, tile_h, tile_padding, island_padding):
    if not all(math.isfinite(v) and v >= 0 for v in (tile_padding, island_padding)):
        raise ValueError("Padding must be finite and non-negative")
    if not all(math.isfinite(v) and v > 2 * tile_padding for v in (tile_w, tile_h)):
        raise ValueError("Tile Padding leaves no usable tile area")


def _inward_float32(value, lower):
    """Round a bound in the non-negative atlas towards the usable area."""
    packed = struct.pack(">f", value)
    rounded, = struct.unpack(">f", packed)
    if (lower and rounded < value) or (not lower and rounded > value):
        bits, = struct.unpack(">I", packed)
        rounded, = struct.unpack(">f", struct.pack(">I", bits + (1 if lower else -1)))
    return rounded


def _plan_tile(islands, tile_pos, tile_w, tile_h, tile_padding, island_padding, allow_upscale,
               *, stored_uvs=False):
    """Pack consecutive islands into shelves at a single scale per tile."""
    if not islands:
        return []
    _validate_padding(tile_w, tile_h, tile_padding, island_padding)
    sizes = [tuple(data["size"]) for data in islands]
    if not all(math.isfinite(v) and v > 0 for size in sizes for v in size):
        raise ValueError("invalid island bounds; unwrap degenerate UV faces")
    x, y = tile_pos
    if not all(math.isfinite(v) for v in (x, y)):
        raise ValueError("non-finite tile coordinates")
    width = tile_w - 2 * tile_padding
    height = tile_h - 2 * tile_padding
    gap = island_padding
    count = len(sizes)

    # Centres of positive-size boxes must be separated by more than the gap
    # on at least one axis. A grid of gap-sized cells gives an upper bound
    # even for layouts that do not use shelves.
    if gap:
        across = math.ceil(Fraction(width) / Fraction(gap))
        down = math.ceil(Fraction(height) / Fraction(gap))
        if count > across * down:
            raise ValueError("required gaps alone rule out this many islands")

    left_edge, bottom_edge = x + tile_padding, y + tile_padding
    right_edge, top_edge = x + tile_w - tile_padding, y + tile_h - tile_padding
    if stored_uvs:
        left_edge = _inward_float32(left_edge, True)
        bottom_edge = _inward_float32(bottom_edge, True)
        right_edge = _inward_float32(right_edge, False)
        top_edge = _inward_float32(top_edge, False)
        width, height = right_edge - left_edge, top_edge - bottom_edge
        if width <= 0 or height <= 0:
            raise ValueError("Tile Padding leaves no usable area at Blender UV precision")
        if gap:
            # Allow for opposite rounding of two adjacent edges in [0, 1].
            gap += 2 ** -24

    def shelves(scale):
        # Minimum total shelf height for each prefix. Trying all possible
        # row breaks avoids false failures when an early wrap groups tall UVs.
        heights = [0.0] + [math.inf] * count
        starts = [0] * (count + 1)
        for start in range(count):
            used = heights[start]
            if not math.isfinite(used):
                continue
            row_w, row_h = 0.0, 0.0
            for end in range(start, count):
                w, h = sizes[end]
                row_w += w * scale
                row_h = max(row_h, h * scale)
                total = used + row_h + (gap if start else 0.0)
                if row_w > width - (end - start) * gap or total > height:
                    break
                if total < heights[end + 1]:
                    heights[end + 1] = total
                    starts[end + 1] = start
        if not math.isfinite(heights[count]):
            return None
        rows = []
        end = count
        while end:
            start = starts[end]
            rows.append((start, end))
            end = start
        return rows[::-1]

    upper = min(width / max(w for w, h in sizes), height / max(h for w, h in sizes))
    if not allow_upscale:
        upper = min(upper, 1.0)
    if not math.isfinite(upper) or upper <= 0:
        raise ValueError("invalid uniform scale")
    rows = shelves(upper)
    scale = upper
    if rows is None:
        scale = 0.0
        for _ in range(48):
            trial = scale + (upper - scale) / 2
            candidate = shelves(trial)
            if candidate is None:
                upper = trial
            else:
                scale, rows = trial, candidate
        if rows is None or scale <= 0:
            raise ValueError("no positive scale fits this island order in rows")

    top = top_edge
    result = []
    for start, end in rows:
        left = left_edge
        for w, h in sizes[start:end]:
            right, bottom = left + w * scale, top - h * scale
            if not all(math.isfinite(v) for v in (left, bottom, right, top)) or right <= left or top <= bottom:
                raise ValueError("an island would collapse or have invalid coordinates at the shared scale")
            result.append((scale, (left, bottom), (left, bottom, right, top)))
            left = right + gap
        top -= max(h for w, h in sizes[start:end]) * scale + gap
    return result


def _validate_tile_layout(boxes, bounds, gap):
    """Return (overlapping pairs, out-of-bounds islands, missing-gap pairs)."""
    overlaps = outside = missing_gap = 0
    for i, box in enumerate(boxes):
        outside += any(box[a] < bounds[a] or box[a + 2] > bounds[a + 2]
                       for a in (0, 1))
        for other in boxes[:i]:
            separation = max(max(box[a] - other[a + 2], other[a] - box[a + 2])
                             for a in (0, 1))
            overlaps += separation < 0
            missing_gap += separation < gap and not math.isclose(separation, gap, rel_tol=1e-15)
    return overlaps, outside, missing_gap


def _uv_edges_match(loop_a, loop_b, uv_layer):
    """Return whether two loops on the same mesh edge are UV-continuous."""
    a_start = loop_a[uv_layer].uv
    a_end = loop_a.link_loop_next[uv_layer].uv
    b_start = loop_b[uv_layer].uv
    b_end = loop_b.link_loop_next[uv_layer].uv

    if loop_a.vert == loop_b.vert:
        return (a_start - b_start).length < UV_EPSILON and (a_end - b_end).length < UV_EPSILON
    return (a_start - b_end).length < UV_EPSILON and (a_end - b_start).length < UV_EPSILON


def _connected_uv_faces(face, uv_layer):
    """Yield faces joined to *face* across UV-continuous shared edges."""
    for loop in face.loops:
        for linked in loop.edge.link_loops:
            if linked.face != face and _uv_edges_match(loop, linked, uv_layer):
                yield linked.face


def _edit_mesh_objects(context):
    """Return mesh objects in Edit Mode from any editor context."""
    objects = list(getattr(context, "objects_in_mode_unique_data", ()) or ())
    if not objects:
        objects = list(getattr(context, "selected_objects", ()) or ())

    edit_object = getattr(context, "edit_object", None)
    if edit_object and edit_object not in objects:
        objects.append(edit_object)

    return [
        obj for obj in objects
        if obj.type == 'MESH' and obj.mode == 'EDIT'
    ]


def _active_uv_layer(obj, bm):
    """Resolve the mesh's chosen UV map by name; never create a layer."""
    active = obj.data.uv_layers.active
    return bm.loops.layers.uv.get(active.name) if active else None


# -----------------------------
# World Orientation Helpers
# -----------------------------
def _snapshot_uv_face_selection(context, objects):
    """Read native Edit BMesh selection without changing mode or selection."""
    mode = context.tool_settings.uv_select_mode
    snapshots = {}
    for obj in objects:
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = _active_uv_layer(obj, bm)
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()
        snapshots[obj] = {
            face.index for face in _get_selected_faces(bm, uv_layer, selection_mode=mode)
        } if uv_layer else set()
    return snapshots


def _get_selected_faces(bm, uv_layer, selected_face_indices=None, selection_mode='VERTEX'):
    """Only complete selected faces participate; partial vertices/edges stay put."""
    if uv_layer is None:
        return []
    selected = []
    for face in bm.faces:
        if face.hide or not face.select:
            continue
        if selected_face_indices is not None:
            chosen = face.index in selected_face_indices
        elif selection_mode == 'FACE':
            chosen = face.uv_select
        elif selection_mode == 'EDGE':
            chosen = all(loop.uv_select_edge for loop in face.loops)
        else:  # Vertex and Island modes both require the full face.
            chosen = all(loop.uv_select_vert for loop in face.loops)
        if chosen:
            selected.append(face)
    return selected

def _island_center(faces, uv_layer):
    total = Vector((0.0, 0.0))
    count = 0
    for f in faces:
        for loop in f.loops:
            total += loop[uv_layer].uv
            count += 1
    return total / count if count else Vector((0.0, 0.0))

def _world_normal_transform(matrix):
    """Transform oriented area vectors, including reflected face winding."""
    linear = matrix.to_3x3()
    # Do not silently substitute an identity transform for zero-scale objects.
    normal_matrix = linear.inverted().transposed()
    return normal_matrix * linear.determinant()


def _island_world_normal(faces, normal_matrix):
    """Return a world-area-weighted normal, or None for unusable geometry."""
    normal_sum = Vector((0.0, 0.0, 0.0))
    total_area = 0.0
    for face in faces:
        # The cofactor transform maps local oriented area to world area.
        area_vector = normal_matrix @ (face.normal * face.calc_area())
        area = area_vector.length
        if not math.isfinite(area):
            return None
        normal_sum += area_vector
        total_area += area
    if total_area == 0.0 or normal_sum.length <= total_area * 1e-8:
        return None
    return normal_sum.normalized()


def _weighted_orientation_angle(angles):
    """Circular mean; reject directions whose weighted agreement is negligible."""
    if not angles:
        return None, "no usable edges"
    total_weight = math.fsum(weight for _, weight in angles)
    sine = math.fsum(sin(angle) * weight for angle, weight in angles)
    cosine = math.fsum(cos(angle) * weight for angle, weight in angles)
    if not all(math.isfinite(value) for value in (total_weight, sine, cosine)):
        return None, "invalid edge directions"
    if total_weight <= 0.0:
        return None, "no usable edges"
    # Scale-independent cancellation tolerance, not an artistic angle cutoff.
    if math.hypot(sine, cosine) <= total_weight * 1e-6:
        return None, "ambiguous orientation"
    return atan2(sine, cosine), None


def _world_orient_island(faces, uv_layer, matrix, normal_matrix):
    avg_normal = _island_world_normal(faces, normal_matrix)
    if avg_normal is None:
        return "SKIPPED", "unusable surface normal"

    abs_n = Vector((abs(avg_normal.x), abs(avg_normal.y), abs(avg_normal.z)))

    if abs_n.z >= abs_n.x and abs_n.z >= abs_n.y:
        x_idx, y_idx = 0, 1
        flip_x = False
        flip_y = avg_normal.z < 0
    elif abs_n.y >= abs_n.x and abs_n.y >= abs_n.z:
        x_idx, y_idx = 0, 2
        flip_x = avg_normal.y > 0
        flip_y = False
    else:
        x_idx, y_idx = 1, 2
        flip_x = avg_normal.x < 0
        flip_y = False

    # Visit one representative per edge in mesh order, independent of sets.
    seen_edges = set()
    calc_loops = []
    for face in sorted(faces, key=lambda face: face.index):
        for loop in face.loops:
            if loop.edge not in seen_edges:
                seen_edges.add(loop.edge)
                calc_loops.append(loop)

    angles = []
    for loop in calc_loops:
        co0 = matrix @ loop.vert.co
        co1 = matrix @ loop.link_loop_next.vert.co
        delta_3d = co1 - co0

        proj_len = abs(delta_3d[x_idx]) + abs(delta_3d[y_idx])
        if proj_len < 1e-8:
            continue

        uv0 = loop[uv_layer].uv
        uv1 = loop.link_loop_next[uv_layer].uv
        delta_uv = uv1 - uv0
        uv_len = delta_uv.length
        if uv_len < 1e-8:
            continue

        dx = delta_3d[x_idx] if not flip_x else -delta_3d[x_idx]
        dy = delta_3d[y_idx] if not flip_y else -delta_3d[y_idx]

        a0 = atan2(dy, dx)
        a1 = atan2(delta_uv.y, delta_uv.x)
        a_delta = atan2(sin(a0 - a1), cos(a0 - a1))

        weight = proj_len * uv_len

        angles.append((a_delta, weight))

    avg_angle, reason = _weighted_orientation_angle(angles)
    if avg_angle is None:
        return "SKIPPED", reason
    if abs(avg_angle) <= 1e-6:
        return "ALIGNED", None

    if abs(avg_angle) > 1e-6:
        center = _island_center(faces, uv_layer)
        ca, sa = cos(avg_angle), sin(avg_angle)
        for f in faces:
            for loop in f.loops:
                uv = loop[uv_layer].uv
                dx = uv.x - center.x
                dy = uv.y - center.y
                uv.x = center.x + dx * ca - dy * sa
                uv.y = center.y + dx * sa + dy * ca
    return "ROTATED", None

def _get_uv_islands(bm, uv_layer):
    islands = []
    visited_faces = set()
    for face in bm.faces:
        if face in visited_faces:
            continue
        island = []
        stack = [face]
        while stack:
            f = stack.pop()
            if f in visited_faces:
                continue
            visited_faces.add(f)
            island.append(f)
            for linked_face in _connected_uv_faces(f, uv_layer):
                if linked_face not in visited_faces:
                    stack.append(linked_face)
        if island:
            islands.append(island)
    return islands

# -----------------------------
# Properties
# -----------------------------
class CS2WDProperties(bpy.types.PropertyGroup):
    # Tile padding hardcoded at 0.01
    
    exclude_edges: bpy.props.BoolProperty(
        name="Exclude Always On/Off",
        default=False,
        description="Exclude Always On/Off"
    )
    
    blinds_open: bpy.props.BoolProperty(
        name="Blinds (Open)",
        default=False,
        description="Windows with open blinds"
    )

    curtains: bpy.props.BoolProperty(
        name="Curtains (Open)",
        default=False,
        description="Windows with open curtains"
    )

    curtains_closed: bpy.props.BoolProperty(
        name="Curtains (Closed)",
        default=False,
        description="Windows with closed curtains"
    )
    
    blinds_vertical: bpy.props.BoolProperty(
        name="Blinds (Vertical)",
        default=False,
        description="Windows with vertical blinds"
    )
    
    blinds_closed: bpy.props.BoolProperty(
        name="Blinds (Closed)",
        default=False,
        description="Windows with closed blinds"
    )
    
    use_specific_tiles: bpy.props.BoolProperty(
        name="Blank",
        default=False,
        description="Blank windows"
    )

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ("commercial", "Non-Residential", "Uses current window-type options"),
            ("residential", "Residential", "Open curtains, closed curtains and blank tile sets"),
        ],
        default="commercial",
        description="Choose distribution mode"
    )

    padding_units: bpy.props.EnumProperty(
        name="Padding Units",
        items=[('UV', "% of Tile", "Set padding as a percentage of one tile's width"),
               ('PIXELS', "Pixels", "Set padding in texture pixels")],
        default='UV'
    )

    atlas_resolution: bpy.props.EnumProperty(
        name="Atlas Resolution",
        items=[(str(size), str(size), f"{size} × {size} pixels")
               for size in (512, 1024, 2048, 4096)]
              + [('CUSTOM', "Custom", "Specify the square atlas size")],
        default='2048'
    )

    custom_resolution: bpy.props.IntProperty(
        name="Custom Size", default=2048, min=1, subtype='PIXEL'
    )

    tile_padding_px: bpy.props.IntProperty(
        name="Tile Padding", default=4, min=0, subtype='PIXEL',
        description="Minimum clearance inside each tile edge"
    )

    island_padding_px: bpy.props.IntProperty(
        name="Island Padding", default=2, min=0, subtype='PIXEL',
        description="Minimum gap between islands within a tile"
    )

    tile_padding: bpy.props.FloatProperty(
        name="Tile Padding",
        default=0.002,
        min=0.0,
        max=0.05,
        subtype='FACTOR',
        description="Minimum tile-edge clearance in atlas UV units (tile width 0.2)"
    )

    island_padding: bpy.props.FloatProperty(
        name="Island Padding",
        default=0.001,
        min=0.0,
        max=0.05,
        subtype='FACTOR',
        description="Minimum island gap in atlas UV units, counted once between islands or rows"
    )

    # Display percentages without migrating saved UV values or enum identifiers.
    tile_padding_percent: bpy.props.FloatProperty(
        name="Tile Padding", default=1.0, min=0.0, max=25.0,
        soft_max=5.0, precision=2, step=10, subtype='PERCENTAGE',
        description="Clearance inside each tile edge as a percentage of one tile's width",
        get=lambda self: self.tile_padding / TILE_PERCENT_UV,
        set=lambda self, value: setattr(self, "tile_padding", value * TILE_PERCENT_UV),
    )

    island_padding_percent: bpy.props.FloatProperty(
        name="Island Padding", default=0.5, min=0.0, max=25.0,
        soft_max=5.0, precision=2, step=10, subtype='PERCENTAGE',
        description="Gap between islands or rows as a percentage of one tile's width",
        get=lambda self: self.island_padding / TILE_PERCENT_UV,
        set=lambda self, value: setattr(self, "island_padding", value * TILE_PERCENT_UV),
    )

    randomize_distribution: bpy.props.BoolProperty(
        name="Randomize Distribution",
        default=False,
        description="Randomly assign islands to available tiles using the seed below"
    )

    random_seed: bpy.props.IntProperty(
        name="Seed",
        default=0,
        min=0,
        description="Seed used when randomizing distribution"
    )

    allow_upscale: bpy.props.BoolProperty(
        name="Allow Upscale",
        default=False,
        description="Allow islands to grow to fit the usable tile area"
    )
    
    def validate_window_selection(self):
        """Ensure at least one window selection option is active"""
        if self.mode == 'commercial':
            selected_count = sum([
                self.blinds_open,
                self.blinds_vertical,
                self.blinds_closed,
                self.use_specific_tiles
            ])
        else:  # residential mode
            selected_count = sum([
                self.curtains,
                self.curtains_closed,
                self.use_specific_tiles
            ])
        # Require at least one active option for the chosen mode
        return selected_count >= 1

    def get_selected_tiles(self):
        """Get tiles based on the selected window type (union for multiple types)"""
        if self.mode == 'commercial':
            tiles = set()
            if self.blinds_open:
                tiles.update([0, 4, 6, 12, 18, 20, 24])
            if self.blinds_vertical:
                tiles.update([2, 8, 10, 14, 16, 22])
            if self.blinds_closed:
                tiles.update([3, 5, 9, 11, 17, 23])
            if self.use_specific_tiles:
                tiles.update([1, 7, 13, 15, 19, 21])
            return sorted(tiles)
        else:
            # Residential presets use the atlas's exact numbered tile sets.
            tiles = set()
            if self.curtains:
                tiles.update(RESI_CUR_TILES)
            if self.curtains_closed:
                tiles.update(RESI_CUR_CLOSED_TILES)
            if self.use_specific_tiles:
                tiles.update(RESI_BLANK_TILES)
            return sorted(tiles)

# -----------------------------
# UV Distribution Operator
# -----------------------------
class CS2WD_OT_DistributeUV(bpy.types.Operator):
    bl_idname = "cs2wd.distribute_uv"
    bl_label = "Distribute"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Distribute selected UV islands across the chosen CS2 window tiles"

    @classmethod
    def poll(cls, context):
        return bool(_edit_mesh_objects(context))

    def _collect_island_data(self, obj, use_uv_sync, selected_face_indices=None):
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = _active_uv_layer(obj, bm)
        bm.faces.ensure_lookup_table()
        if uv_layer is None:
            return [], bm

        islands = []
        visited = set()
        if use_uv_sync:
            faces_to_process = [f for f in bm.faces if f.select and not f.hide]
        else:
            faces_to_process = [
                f for f in _get_selected_faces(bm, uv_layer, selected_face_indices)
                if not f.hide
            ]

        if not faces_to_process:
            return [], bm

        selected_faces = set(faces_to_process)
        for face in faces_to_process:
            if face in visited:
                continue
            island = set()
            stack = [face]
            while stack:
                f = stack.pop()
                if f in island:
                    continue
                island.add(f)
                visited.add(f)
                for linked_face in _connected_uv_faces(f, uv_layer):
                    if linked_face in selected_faces and linked_face not in island:
                        stack.append(linked_face)
            islands.append(island)

        data_list = []
        for island in islands:
            uvs = []
            coords = []
            for f in island:
                for l in f.loops:
                    uvs.append(l[uv_layer])
                    coords.append(l[uv_layer].uv.copy())
            if not coords:
                continue
            min_x = min(v.x for v in coords)
            max_x = max(v.x for v in coords)
            min_y = min(v.y for v in coords)
            max_y = max(v.y for v in coords)
            size = (max_x - min_x, max_y - min_y)
            centroid = Vector((0.0, 0.0))
            for c in coords:
                centroid += c
            centroid /= len(coords)
            data_list.append({
                "uvs": uvs,
                "coords": coords,
                "min": Vector((min_x, min_y)),
                "size": size,
                "centroid": centroid,
                "obj": obj,
            })
        return data_list, bm

    def execute(self, context):
        objects = _edit_mesh_objects(context)
        if not objects:
            return {'CANCELLED'}

        props = context.scene.cs2wd_props
        if not props.validate_window_selection():
            self.report({'WARNING'}, "Select at least one window category for the current mode")
            return {'CANCELLED'}
        if not any(obj.data.uv_layers.active for obj in objects):
            self.report({'WARNING'}, "Meshes need an existing active UV map")
            return {'CANCELLED'}
        selected_uv_faces = (
            {}
            if context.tool_settings.use_uv_select_sync
            else _snapshot_uv_face_selection(context, objects)
        )

        tile_padding, island_padding = _effective_padding(props)

        if DEBUG_TILE_SCALES:
            print("cs2wd OBJECTS:", [o.name for o in objects])

        # Collect islands from all selected objects
        island_data = []
        obj_bm_map = {}
        for obj in objects:
            data_list, bm = self._collect_island_data(
                obj,
                context.tool_settings.use_uv_select_sync,
                selected_uv_faces.get(obj),
            )
            island_data.extend(data_list)
            obj_bm_map[obj] = bm

        if not island_data:
            self.report({'WARNING'}, "Select one or more UV islands")
            return {'CANCELLED'}

        # Tile grid
        cols = rows = 5
        tile_w = 1.0 / cols
        tile_h = 1.0 / rows

        tiles = []
        for r in range(rows):
            for c in range(cols):
                tiles.append({
                    "pos": (c / cols, (rows - 1 - r) / rows),
                    "islands": []
                })

        tile_indices = props.get_selected_tiles()
        if props.exclude_edges:
            tile_indices = [i for i in tile_indices if i not in (0, 24)]
        if not tile_indices:
            self.report({'WARNING'}, "No usable atlas tiles in the selected categories")
            return {'CANCELLED'}

        # Stable order makes repeated runs reproducible.  Randomization is opt-in.
        island_data.sort(key=lambda data: (data["obj"].name, data["min"].y, data["min"].x))
        if props.randomize_distribution:
            random.Random(props.random_seed).shuffle(island_data)

        for i, data in enumerate(island_data):
            tiles[tile_indices[i % len(tile_indices)]]["islands"].append(data)

        tiles_used = sum(bool(tile["islands"]) for tile in tiles)
        summary = f"{len(island_data)} islands, {tiles_used} tiles used"

        padding = f"Tile Padding {tile_padding:.6g} UV, Island Padding {island_padding:.6g} UV"
        upscale = "on" if props.allow_upscale else "off"
        # Keep the original and target coordinates until every tile has passed.
        placements = []
        for ti, tile in enumerate(tiles):
            if not tile["islands"]:
                continue
            x, y = tile["pos"]
            bounds = (x + tile_padding, y + tile_padding,
                      x + tile_w - tile_padding, y + tile_h - tile_padding)
            try:
                if not all(math.isfinite(v) for data in tile["islands"]
                           for co in data["coords"] for v in co):
                    raise ValueError("non-finite source UVs; re-unwrap the affected faces")
                plan = _plan_tile(tile["islands"], tile["pos"], tile_w, tile_h,
                                  tile_padding, island_padding, props.allow_upscale,
                                  stored_uvs=True)
                boxes = []
                for data, (scale, offset, _) in zip(tile["islands"], plan):
                    origin = data["min"]
                    # Keep intermediate values in double precision; round only
                    # when constructing the Vector that Blender will store.
                    writes = [
                        (uv, orig, Vector(tuple((orig[a] - origin[a]) * scale + offset[a]
                                                for a in (0, 1))))
                        for uv, orig in zip(data["uvs"], data["coords"])
                    ]
                    coords = [target for _, _, target in writes]
                    if not coords or not all(math.isfinite(v) for co in coords for v in co):
                        raise ValueError("invalid target UV coordinates")
                    lo = [min(co[a] for co in coords) for a in (0, 1)]
                    hi = [max(co[a] for co in coords) for a in (0, 1)]
                    if any(high <= low for low, high in zip(lo, hi)):
                        raise ValueError("an island would collapse at Blender UV precision")
                    boxes.append((*lo, *hi))
                    placements.extend(writes)
                overlaps, outside, missing_gap = _validate_tile_layout(boxes, bounds, island_padding)
                if overlaps or outside or missing_gap:
                    raise ValueError(f"stored UVs would have {overlaps} overlaps, {outside} out of bounds, "
                                     f"and {missing_gap} pairs below the required spacing")
            except ValueError as exc:
                self.report({'WARNING'}, f"Insufficient tile space in tile {ti + 1} "
                            f"({len(tile['islands'])} islands; {padding}; Allow Upscale {upscale}): "
                            f"{exc}. Reduce padding, enable more categories, or select fewer islands.")
                return {'CANCELLED'}

        # Commit only after the entire atlas passes validation.
        try:
            for uv, orig, target in placements:
                uv.uv = target
        except Exception:
            for uv, orig, target in placements:
                uv.uv = orig
            for obj in objects:
                bmesh.update_edit_mesh(obj.data)
            self.report({'WARNING'}, "UV placement failed; original coordinates restored")
            return {'CANCELLED'}

        # Update all objects
        updated = set()
        for obj in objects:
            bm = obj_bm_map.get(obj)
            if bm:
                bmesh.update_edit_mesh(obj.data)
                updated.add(obj.name)

        if DEBUG_TILE_SCALES:
            print(f"cs2wd DISTRIBUTE: distributed {len(island_data)} islands across {len(updated)} object(s)")
        self.report({'INFO'}, f"{summary}, 0 overlaps, 0 out of bounds")
        return {'FINISHED'}

# -----------------------------
# World Orientation Operator
# -----------------------------
class CS2WD_OT_WorldOrient(bpy.types.Operator):
    bl_idname = "cs2wd.world_orient"
    bl_label = "Orientate UVs"
    bl_description = "Orientate selected UV islands to world orientation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(obj.data.uv_layers.active for obj in _edit_mesh_objects(context))

    def execute(self, context):
        objects = [obj for obj in _edit_mesh_objects(context) if obj.data.uv_layers.active]
        selected_uv_faces = (
            {}
            if context.tool_settings.use_uv_select_sync
            else _snapshot_uv_face_selection(context, objects)
        )
        counts = {"ROTATED": 0, "ALIGNED": 0, "SKIPPED": 0}
        reasons = {}
        invalid_objects = 0
        for obj in objects:
            me = obj.data
            bm = bmesh.from_edit_mesh(me)
            uv_layer = _active_uv_layer(obj, bm)
            bm.faces.ensure_lookup_table()
            if uv_layer is None:
                continue
            matrix = obj.matrix_world
            try:
                normal_matrix = _world_normal_transform(matrix)
            except ValueError:
                invalid_objects += 1
                continue

            if context.tool_settings.use_uv_select_sync:
                selected_faces = [face for face in bm.faces if face.select and not face.hide]
            else:
                selected_faces = _get_selected_faces(
                    bm, uv_layer, selected_uv_faces.get(obj)
                )
            if not selected_faces:
                continue

            islands = _get_uv_islands(bm, uv_layer)
            selected_faces = set(selected_faces)
            rotated = False
            for island in islands:
                if any(f in selected_faces for f in island):
                    outcome, reason = _world_orient_island(island, uv_layer, matrix, normal_matrix)
                    counts[outcome] += 1
                    rotated |= outcome == "ROTATED"
                    if reason:
                        reasons[reason] = reasons.get(reason, 0) + 1

            if rotated:
                bmesh.update_edit_mesh(me)
        if invalid_objects:
            reasons["object(s) with zero scale"] = invalid_objects
        if not any(counts.values()) and not invalid_objects:
            self.report({'WARNING'}, "No UV islands selected")
            return {'CANCELLED'}
        successful = counts["ROTATED"] + counts["ALIGNED"]
        message = (f"Rotated {counts['ROTATED']} island(s); "
                   f"{counts['ALIGNED']} already aligned; skipped {counts['SKIPPED']}")
        if reasons:
            message += " (" + "; ".join(
                f"{count} {reason}" for reason, count in sorted(reasons.items())
            ) + ")"
        self.report({'INFO'} if successful else {'WARNING'}, message)
        return {'FINISHED'} if successful else {'CANCELLED'}

# -----------------------------
# Main Panel
# -----------------------------
class CS2WD_PT_MainPanel(bpy.types.Panel):
    bl_label = "MW CS2 Window Distributor"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "MW CS2 Win Dist"

    def draw(self, context):
        layout = self.layout
        props = context.scene.cs2wd_props

        layout.prop(props, "exclude_edges")
        layout.separator()
        # Mode selector (exclusive)
        layout.prop(props, "mode")
        layout.separator()
        # UI toggles depending on mode
        if props.mode == 'commercial':
            layout.prop(props, "blinds_vertical")
            layout.prop(props, "blinds_open")
            layout.prop(props, "blinds_closed")
            layout.prop(props, "use_specific_tiles")
        else:
            layout.prop(props, "curtains")
            layout.prop(props, "curtains_closed")
            layout.prop(props, "use_specific_tiles")
        layout.separator()
        layout.label(text="Packing")
        layout.prop(props, "padding_units", expand=True)
        if props.padding_units == 'PIXELS':
            layout.prop(props, "atlas_resolution")
            if props.atlas_resolution == 'CUSTOM':
                layout.prop(props, "custom_resolution")
            layout.prop(props, "tile_padding_px")
            layout.prop(props, "island_padding_px")
            edge, gap = _effective_padding(props)
            layout.label(text=f"UV: Edge {edge:.6g} / Gap {gap:.6g}")
        else:
            layout.prop(props, "tile_padding_percent")
            layout.prop(props, "island_padding_percent")
        try:
            _validate_padding(0.2, 0.2, *_effective_padding(props))
        except ValueError as exc:
            layout.label(text=str(exc), icon='ERROR')
        layout.prop(props, "allow_upscale")
        layout.prop(props, "randomize_distribution")
        if props.randomize_distribution:
            layout.prop(props, "random_seed")
        layout.separator()
        # Orientate UVs button
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("cs2wd.world_orient", icon='WORLD')
        layout.separator()
        # Distribute button
        layout.operator("cs2wd.distribute_uv", icon='UV')

# -----------------------------
# Register
# -----------------------------
classes = (
    CS2WDProperties,
    CS2WD_OT_DistributeUV,
    CS2WD_OT_WorldOrient,
    CS2WD_PT_MainPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cs2wd_props = bpy.props.PointerProperty(type=CS2WDProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.cs2wd_props

if __name__ == "__main__":
    register()
