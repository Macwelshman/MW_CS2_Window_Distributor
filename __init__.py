bl_info = {
    "name": "MW CS2 Window Distributor",
    "author": "Macwelshman",
    "version": (2, 6, 0),
    "blender": (3, 0, 0),
    "location": "UV Editor > Sidebar",
    "description": "Distribute windows across the CS2 window space.",
    "category": "UV",
}

import bpy
import bmesh
import random
from mathutils import Vector
import math
PATCH_STEP1_DUMMY = True

from math import sin, cos, atan2

# Blender 5.0 compatibility flag (best-effort, feature-detection-based)
try:
    _BLENDER_MAJOR = bpy.app.version[0]
    IS_BLENDER_5 = _BLENDER_MAJOR >= 5
except Exception:
    IS_BLENDER_5 = False
DEBUG_TILE_SCALES = True  # Set to True to print per-tile scale debugging information
TILE_SCALE_CAP = 1.25

# Residential mode tile sets (0-based indices)
RESI_CUR_TILES = [2, 3, 5, 8, 9, 10, 11, 14, 16, 17, 22, 23]
RESI_BLANK_TILES = [0, 1, 4, 6, 7, 12, 13, 15, 18, 19, 20, 21, 24]

def _tile_mean_scale(islands, cell_w, cell_h):
    """Return uniform scale for all islands in a tile based on mean island size."""
    if not islands:
        return 1.0
    mean_w = sum(d["size"].x for d in islands) / len(islands)
    mean_h = sum(d["size"].y for d in islands) / len(islands)
    eps = 1e-8
    return min(cell_w / max(mean_w, eps), cell_h / max(mean_h, eps), 1.0)

# -----------------------------
# World Orientation Helpers
# -----------------------------
def _get_selected_faces(bm, uv_layer):
    selected = []
    for f in bm.faces:
        if not f.select:
            continue
        try:
            if not all(loop[uv_layer].select for loop in f.loops):
                continue
        except AttributeError:
            pass
        selected.append(f)
    return selected

def _island_center(faces, uv_layer):
    total = Vector((0.0, 0.0))
    count = 0
    for f in faces:
        for loop in f.loops:
            total += loop[uv_layer].uv
            count += 1
    return total / count if count else Vector((0.0, 0.0))

def _world_orient_island(faces, uv_layer, matrix):
    avg_normal = Vector((0.0, 0.0, 0.0))
    for f in faces:
        world_n = (matrix.to_3x3() @ f.normal).normalized()
        avg_normal += world_n
    avg_normal /= len(faces)
    if avg_normal.length < 1e-8:
        return
    avg_normal.normalize()

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

    island_loops = {loop for f in faces for loop in f.loops}
    island_edges = {edge for f in faces for edge in f.edges}

    calc_loops = []
    for edge in island_edges:
        uv_pairs = []
        for vert in edge.verts:
            for loop in vert.link_loops:
                if loop in island_loops:
                    uv_pairs.append(loop[uv_layer].uv.to_tuple(5))
                    break
        if len(set(uv_pairs)) == 2:
            for loop in edge.link_loops:
                if loop in island_loops:
                    calc_loops.append(loop)
                    break

    if not calc_loops:
        calc_loops = list(island_loops)

    total_weight = 0.0
    avg_angle = 0.0
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

        if total_weight == 0.0:
            avg_angle = a_delta
            total_weight = weight
        else:
            diff = a_delta - avg_angle
            diff = atan2(sin(diff), cos(diff))
            avg_angle += diff * (weight / (total_weight + weight))
            total_weight += weight

    if total_weight == 0.0:
        return

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
            for loop in f.loops:
                for linked in loop.vert.link_loops:
                    if linked.face in visited_faces:
                        continue
                    if (loop[uv_layer].uv - linked[uv_layer].uv).length < 1e-6:
                        stack.append(linked.face)
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
        name="Curtains",
        default=False,
        description="Windows with curtains"
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
            ("commercial", "Commercial", "Uses current window-type options"),
            ("residential", "Residential", "Blinds/Blank tile sets"),
        ],
        default="commercial",
        description="Choose distribution mode"
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
            if not tiles:
                return list(range(25))
            return sorted(tiles)
        else:
            # Residential mode uses Curtains + Blank presets
            tiles = set()
            if self.curtains:
                tiles.update(RESI_CUR_TILES)
            if self.use_specific_tiles:
                tiles.update(RESI_BLANK_TILES)
            if not tiles:
                tiles.update(RESI_CUR_TILES)
            return sorted(tiles)

# -----------------------------
# UV Distribution Operator
# -----------------------------
class CS2WD_OT_DistributeUV(bpy.types.Operator):
    bl_idname = "cs2wd.distribute_uv"
    bl_label = "Distribute"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Select one or more decoration types"

    @classmethod
    def poll(cls, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            return False
        props = getattr(context.scene, 'cs2wd_props', None)
        if not props:
            return False
        try:
            return bool(props.validate_window_selection())
        except Exception:
            return False

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}
        if context.mode != 'EDIT_MESH':
            return {'CANCELLED'}

        props = context.scene.cs2wd_props

        tile_padding = 0.0
        island_padding = 0.001
        # Determine current mode for user feedback (e.g., "just blank" if only Blank)
        def _mode(p):
            opts = [
                ("Blinds Open", p.blinds_open),
                ("Blinds Vertical", p.blinds_vertical),
                ("Blinds Closed", p.blinds_closed),
                ("Blank", p.use_specific_tiles),
            ]
            active = [name for name, val in opts if val]
            if not active:
                return "none"
            if len(active) == 1:
                if "Blank" in active:
                    return "just blank"
                return active[0].lower()
            return "mixed"
        mode_label = _mode(props)
        if DEBUG_TILE_SCALES:
            print("cs2wd MODE:", mode_label)

        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.verify()
        bm.faces.ensure_lookup_table()

        # -----------------------------
        # 1. Detect UV islands (only for selected faces)
        # -----------------------------
        islands = []
        visited = set()

        # Simple face selection for now
        selected_faces = [f for f in bm.faces if f.select]
        faces_to_process = selected_faces if selected_faces else bm.faces

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

                for loop in f.loops:
                    for linked in loop.vert.link_loops:
                        if linked.face in island:
                            continue
                        if (loop[uv_layer].uv - linked[uv_layer].uv).length < 1e-6:
                            stack.append(linked.face)

            islands.append(island)

        if not islands:
            return {'CANCELLED'}

        # -----------------------------
        # 2. Cache island data
        # -----------------------------
        island_data = []

        for island in islands:
            uvs = []
            coords = []

            for f in island:
                for l in f.loops:
                    uvs.append(l[uv_layer])
                    coords.append(l[uv_layer].uv.copy())

            min_x = min(v.x for v in coords)
            max_x = max(v.x for v in coords)
            min_y = min(v.y for v in coords)
            max_y = max(v.y for v in coords)

            size = Vector((max_x - min_x, max_y - min_y))

            # Compute centroid of island UVs for rotation anchor
            if coords:
                centroid = Vector((0.0, 0.0))
                for c in coords:
                    centroid += c
                centroid /= len(coords)
            else:
                centroid = Vector((min_x, min_y))
            island_data.append({
                "uvs": uvs,
                "coords": coords,
                "min": Vector((min_x, min_y)),
                "size": size,
                "centroid": centroid
            })

        # -----------------------------
        # 3. Generate tiles (5x5)
        # -----------------------------
        cols = rows = 5
        tile_w = 1.0 / cols
        tile_h = 1.0 / rows

        tiles = []
        for r in range(rows):
            for c in range(cols):
                tiles.append({
                    "pos": Vector((c * tile_w, 1.0 - (r + 1) * tile_h)),
                    "islands": []
                })

        # -----------------------------
        # 4. Assign tiles to islands based on selections
        # -----------------------------
        tile_indices = props.get_selected_tiles()
        # Safety: ensure we have at least one tile to map islands to
        if not tile_indices:
            tile_indices = list(range(25))
        # Apply exclude edges if active
        if props.exclude_edges:
            tile_indices = [i for i in tile_indices if i not in (0, 24)]
            # If exclusion leaves no tiles, fall back to all non-edge tiles
            if not tile_indices:
                tile_indices = [i for i in range(25) if i not in (0, 24)]

        # Reset tile islands so each distribution recomputes scaling from scratch
        for t in tiles:
            t["islands"] = []
        random.shuffle(island_data)

        for i, data in enumerate(island_data):
            tiles[tile_indices[i % len(tile_indices)]]["islands"].append(data)

        # Compute global max island dimensions for consistent per-tile scaling
        # across all tiles to ensure uniform island sizes
        global_max_w = 1.0
        global_max_h = 1.0
        if island_data:
            global_max_w = max(d["size"].x for d in island_data) or 1.0
            global_max_h = max(d["size"].y for d in island_data) or 1.0

        # -----------------------------
        # 5. Place islands per tile with PER-TILE UNIFORM SCALE
        # -----------------------------
        for ti, tile in enumerate(tiles):
            islands_in_tile = tile["islands"]
            if not islands_in_tile:
                continue

            # Compute grid size (rows x cols) for this tile
            n = len(islands_in_tile)
            grid_cols = math.ceil(math.sqrt(n))
            grid_rows = math.ceil(n / grid_cols)

            # Pre-compute tile cell size for this tile
            cell_w = (tile_w - 2 * tile_padding - (grid_cols - 1) * island_padding) / grid_cols
            cell_h = (tile_h - 2 * tile_padding - (grid_rows - 1) * island_padding) / grid_rows
            # Step 2A: per tile mean scale (robust to outliers)
            tile_scale = _tile_mean_scale(islands_in_tile, cell_w, cell_h)
            if DEBUG_TILE_SCALES:
                print(f"cs2wd DEBUG: tile {ti} n={n} cell_w={cell_w} cell_h={cell_h} tile_scale={tile_scale:.6f}")
            # Orientation removed: no rotation; keep 2D centering only

            for idx, data in enumerate(islands_in_tile):
                col = idx % grid_cols
                row = idx // grid_cols

                # Cell top-left position
                cell_x = tile["pos"].x + tile_padding + col * (cell_w + island_padding)
                cell_y = tile["pos"].y + tile_h - tile_padding - (row + 1) * cell_h - row * island_padding
                # Bounds of the sub-cell area within this tile cell
                subcell_min_x = cell_x
                subcell_max_x = cell_x + cell_w
                subcell_min_y = cell_y
                subcell_max_y = cell_y + cell_h

                # Fill each island cell by its own height/width, preserving aspect ratio
                width = data["size"].x
                height = data["size"].y
                cell_w_eff = max(cell_w - 2 * island_padding, 0.0)
                cell_h_eff = max(cell_h - 2 * island_padding, 0.0)
                eps = 1e-8
                scale_i = min(cell_w_eff / max(width, eps), cell_h_eff / max(height, eps), 1.0)
                # Enforce tile-wide mean-based scale as an upper bound
                scale_final = min(scale_i, tile_scale)

                offset_i = Vector((
                    cell_x + (cell_w - width * scale_final) * 0.5 - data["min"].x * scale_final,
                    cell_y + (cell_h - height * scale_final) * 0.5 - data["min"].y * scale_final
                ))

                for uv, orig in zip(data["uvs"], data["coords"]):
                    uv.uv = orig * scale_final + offset_i
                    # Clamp to the sub-cell bounds to avoid spilling outside tile space
                    uv.uv.x = max(min(uv.uv.x, subcell_max_x), subcell_min_x)
                    uv.uv.y = max(min(uv.uv.y, subcell_max_y), subcell_min_y)

        bmesh.update_edit_mesh(obj.data)
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
        obj = context.object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT' and obj.data.uv_layers

    def execute(self, context):
        obj = context.object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        uv_layer = bm.loops.layers.uv.verify()
        bm.faces.ensure_lookup_table()
        matrix = obj.matrix_world

        selected_faces = _get_selected_faces(bm, uv_layer)
        if not selected_faces:
            self.report({'WARNING'}, "No UV islands selected")
            return {'CANCELLED'}

        islands = _get_uv_islands(bm, uv_layer)
        processed = 0
        for island in islands:
            if any(f in selected_faces for f in island):
                _world_orient_island(island, uv_layer, matrix)
                processed += 1

        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, f"World oriented {processed} island(s)")
        return {'FINISHED'}

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
            layout.prop(props, "use_specific_tiles")
        layout.separator()
        # Orientate UVs button
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("cs2wd.world_orient", icon='WORLD')
        layout.separator()
        # Distribute button
        op = layout.operator("cs2wd.distribute_uv", icon='UV')

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
