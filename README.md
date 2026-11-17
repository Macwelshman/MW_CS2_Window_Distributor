# MW CS2 Window Distributor

A Blender UV Editor add-on for distributing window UV islands across the **5 × 5 window texture atlas used by Cities: Skylines II**.

The add-on places selected UV islands into predefined non-residential or residential window tiles, keeps distribution repeatable by default, and provides controls for padding, scaling, randomisation, and world-aligned UV orientation.

## Features

- Distributes selected UV islands across a 5 × 5 CS2 window atlas.
- Non-Residential and residential window presets.
- Supports one or more mesh objects in Edit Mode.
- Preserves each island's aspect ratio.
- Uses a consistent scale for all islands placed within the same tile.
- Optional upscaling to make better use of the available tile space.
- Adjustable tile-edge and inter-island padding.
- Optional seeded random distribution.
- World-orients selected UV islands from their mesh surface orientation.
- Supports UV Sync Selection on or off.
- Reads native Blender 5.2 BMesh UV selection without leaving Edit Mode.
- Distribution and orientation operations support Undo.

## Requirements

- **Blender 5.2 or later**
- A mesh with an existing UV map
- Window UV islands prepared for placement within the CS2 window atlas

The current source version is **2.7.8**.

## Installation

### Install from the MW Blender Extensions repository

1. Open **Edit → Preferences → Get Extensions**.
2. Open the repositories menu and add:
   `https://raw.githubusercontent.com/Macwelshman/MW-Blender-Extensions/main/index.json`
3. Sync the repository.
4. Search for **MW CS2 Window Distributor** and click **Install**.

Blender will offer future published versions through **Check for Updates**. If
you previously installed the legacy ZIP, remove it once and reinstall from the
MW repository so Blender can manage subsequent updates.

### Install the packaged add-on

1. Download the add-on ZIP from the repository's releases or `dist` folder.
2. Open Blender.
3. Go to **Edit → Preferences → Add-ons**.
4. Click the menu in the upper-right corner and choose **Install from Disk**.
5. Select the add-on ZIP.
6. Enable **MW CS2 Window Distributor** if Blender does not enable it automatically.

Do not extract the installation ZIP before installing it through Blender.

### Install from the source folder

Build the Extension package from the repository root so `__init__.py` and
`blender_manifest.toml` are both at the ZIP root, then install it through
**Edit → Preferences → Get Extensions → Install from Disk**.

## Location

Open a **UV Editor**, then press `N` to show the sidebar.

The add-on is located under:

```text
UV Editor → Sidebar → MW CS2 Win Dist
```

## Basic usage

1. Select one or more mesh objects.
2. Enter **Edit Mode**.
3. Select the UV islands you want to distribute.
4. Open the **MW CS2 Win Dist** panel in the UV Editor sidebar.
5. Choose **Non-Residential** or **Residential** mode.
6. Enable one or more window categories.
7. Adjust the packing options when needed.
8. Click **Distribute**.

The selected islands will be assigned across the enabled atlas tiles. When more islands are selected than there are available tiles, the add-on cycles through the selected tiles and packs multiple islands into each tile.

## Selecting UV islands

The add-on works with **UV Sync Selection** either enabled or disabled.

### UV Sync Selection enabled

Select the relevant mesh faces in Edit Mode. Only those selected faces will be distributed.

### UV Sync Selection disabled

Select complete UV faces or islands in the UV Editor. Vertex mode requires every vertex of a face; Edge mode requires every edge; Face mode uses native face selection. Island selection is supported through Blender's island-selection toggle. Partial faces stay unchanged.

Unselected faces stay unchanged, including faces connected to selected UVs. To make a second pass, deselect all UVs, select only the windows to change, switch the enabled window categories, then click **Distribute** again. For example, distribute Curtains first, then select a few windows and run a Blank-only pass.

If Blender reports **Select one or more UV islands**, check that the full islands are selected rather than only individual UV vertices or edges.

## Distribution modes

### Non-Residential

Non-Residential mode provides four tile groups:

- **Blinds (Vertical)**
- **Blinds (Open)**
- **Blinds (Closed)**
- **Blank**

You can enable several groups together. The add-on distributes islands across the combined set of corresponding atlas tiles.

### Residential

Residential mode provides:

- **Curtains (Open)**: tiles 3, 9, 11, 15, 17 and 23.
- **Curtains (Closed)**: tiles 4, 6, 10, 12, 18 and 24.
- **Blank**: tiles 1, 2, 5, 7, 8, 13, 14, 16, 19, 20, 21, 22 and 25.

Enable one or more groups to combine their tile sets. With no category selected in the current mode, distribution cancels; it does not fall back to other categories. Tile numbering runs left to right, starting at the top-left. **Exclude Always On/Off** removes tiles 1 and 25 in either mode when enabled.

## Controls

### Exclude Always On/Off

Excludes the first and last atlas tiles from distribution. These correspond to the two edge tiles reserved by the add-on as always-on/always-off variants.

Under **Packing**, the default **% of Tile** mode measures padding relative to
the width of one tile, independent of texture resolution. Use **Pixels** when
you need a specific texel gap, and select the full square atlas resolution
(512, 1024, 2048, 4096, or **Custom**). Enter Tile Padding and Island Padding
in pixels. The readout below the fields shows the equivalent atlas UV distances:
4 px on a 2048 px atlas is 4 ÷ 2048 = 0.001953125 UV. Use the full atlas size,
not the size of one tile.

Previously saved UV padding settings appear as equivalent percentages. The
**% of Tile** and **Pixels** modes store separate values, so switching back restores the previous settings
for that mode. Tile Padding applies on both sides of each tile, so it must
be less than one tenth of the atlas resolution. The panel flags padding that
leaves no tile area. If the assigned islands and their spacing cannot fit,
distribution cancels before editing any UVs.

### Tile Padding

Adds space between the UV islands and the outer edge of each atlas tile.

- Default: **1%** per edge (0.002 atlas UV), or **4 px** in Pixels mode.
- Percentage range: **0–25%** of one tile.

Increase this slightly if texture filtering or mipmapping causes neighbouring tiles to bleed into the selected window.

### Island Padding

Adds spacing between multiple islands packed into the same atlas tile.

- Default: **0.5%** (0.001 atlas UV), or **2 px** in Pixels mode.
- Percentage range: **0–25%** of one tile.

Very high values can leave too little room for the UV islands. Distribution validates every tile before writing any UV coordinates and cancels with a warning if there is insufficient space. Original UVs remain unchanged on failure.

### Allow Upscale

Allows islands to grow together to use more of their assigned tile.

When disabled, islands can be reduced to fit but will not be enlarged beyond their current UV scale. When enabled, the add-on may enlarge them while preserving their aspect ratio.

### Randomize Distribution

Randomises which selected island is assigned to each available tile.

When disabled, islands are processed in a stable order based on object name and UV position, making repeated runs predictable.

### Seed

Controls the random arrangement when **Randomize Distribution** is enabled.

The same selection and seed produce the same distribution. Change the seed to generate a different arrangement.

## Orientate UVs

The **Orientate UVs** button rotates selected islands to follow the world orientation of their mesh surfaces.

This can help keep windows consistently upright across differently oriented walls.

1. Select the islands or corresponding mesh faces.
2. Object rotation and non-zero scale can remain unapplied.
3. Click **Orientate UVs**.
4. Inspect the result in the UV Editor.
5. Click **Distribute** when ready.

The operator uses world-area-weighted surface normals and a weighted circular average of edge directions. It reports rotated, already aligned, and skipped islands separately, including reasons for skipping. Conflicting directions and unusable geometry are left unchanged; zero-scale transforms are rejected. Unusual, curved, or irregular geometry may still require manual adjustment. Orient islands before distributing them: rotation after packing can move UVs beyond their tile.

## Multi-object workflow

Both Orientate UVs and Distribute use each mesh's active UV map and support several mesh objects in Edit Mode. Meshes without UV maps are skipped; neither operator creates a map. Orientation uses each object's own world transform and reports combined results.

1. Select all required mesh objects.
2. Enter multi-object Edit Mode.
3. Select the required faces or UV islands on each object.
4. Click **Orientate UVs** if needed, then **Distribute**.

The add-on gathers the selected islands from all editable mesh objects, distributes them as one combined set, and updates each object afterwards.

## Packing behaviour

Each tile starts at its padded upper-left corner. Islands advance left to right by their actual width plus Island Padding. Each new row starts below the tallest island in the preceding row, with the same gap. The add-on chooses row breaks and one shared scale per tile, preserving each island's proportions.

Distribution validates the full atlas before writing UVs. The operator reports the number of islands, tiles used, overlaps and out-of-bounds islands. If a layout cannot fit, reduce padding, enable more tile categories, or select fewer islands and try again.

The warning identifies the failing tile and its padding settings. Some layouts are impossible from the minimum gaps alone. Other failures may reflect the row layout, island order or Blender's UV precision; the add-on does not try every possible arrangement.

## Recommended workflow

1. Apply object scale where appropriate with `Ctrl+A → Scale`.
2. Create and check the object's UV map.
3. Separate window faces into clean UV islands.
4. Use **Orientate UVs** to align selected windows.
5. Choose the required non-residential or residential window groups.
6. Start with low padding values.
7. Run **Distribute**.
8. Check the atlas placement and texture preview.
9. Adjust the seed, padding, or enabled tile groups and run again if needed.

## Troubleshooting

### The panel is not visible

Make sure the current area is a **UV Editor**, press `N`, and select the **MW CS2 Win Dist** tab.

Also confirm that the add-on is enabled under **Edit → Preferences → Add-ons**.

### Distribute does nothing

Confirm that:

- At least one mesh object is in Edit Mode.
- The object has a UV map.
- Complete faces or UV islands are selected.
- At least one window group is enabled.

### The wrong faces are distributed

Check the state of **UV Sync Selection**:

- With sync enabled, the add-on uses selected mesh faces.
- With sync disabled, it uses fully selected UV faces and islands.

### Islands are too small

Enable **Allow Upscale** or reduce **Tile Padding** and **Island Padding**.

### Islands overlap or have too little space

Reduce the number of islands assigned to each tile by enabling more tile categories, or lower the padding values if they leave insufficient usable space.

### The distribution changes unexpectedly

Leave **Randomize Distribution** disabled for stable placement. When randomisation is enabled, keep the same seed to reproduce an arrangement.

### UVs rotate incorrectly

Apply the object's rotation and scale, then try **Orientate UVs** again. Curved, angled, or topologically irregular window geometry may need manual rotation.

### Texture bleeding appears around a tile

Increase **Tile Padding** slightly. Final requirements depend on the atlas resolution, mipmapping, and the CS2 material setup.

## Updating

Repository installations use Blender's normal **Check for Updates** workflow.
Manual installations must be replaced with the newer release ZIP.

The version installed from the current source should appear as **2.7.8**.

## Development

The add-on implementation remains in a single `__init__.py` file. Extension
metadata is declared separately in `blender_manifest.toml`.

A basic syntax check can be run from the repository root with:

```bash
python3 -B -c "import ast, pathlib; ast.parse(pathlib.Path('__init__.py').read_text())"
```

### Repository structure

```text
MW_CS2_Window_Distributor/
├── __init__.py
├── blender_manifest.toml
├── README.md
└── dist/
    └── mw_cs2_window_distributor-2.7.8.zip
```

## Disclaimer

This is an independent community tool and is not affiliated with or endorsed by **Iceflake Studios** or **Paradox Interactive**.

Cities: Skylines II and its associated names and trademarks belong to their respective owners.

## Version 2.7.5

- Selected-only distribution preserves unselected connected UV faces.
- Separate residential open and closed curtain presets.
- Non-Residential mode label; exclusion of tiles 1 and 25 remains available in both modes.
- World-space UV orientation fixes and Blender 5.2 compatibility.
- Updated [user guide](docs/USER_GUIDE.md) and [PDF guide](docs/MW_CS2_Window_Distributor_Guide.pdf).

## Version 2.7.6

- Fixed Orientate UVs processing only the active object during multi-object editing.
- All participating meshes with UV maps are now processed using their own world transforms and UV selections.
- Objects with zero scale are reported without preventing valid objects from being processed.
- Orientation algorithm, atlas distribution and existing controls are unchanged.
- Validated in Blender 5.2.2 with UV Sync Selection on/off, different active objects, repeated execution and multi-object Undo; user confirmed the installed fix.

Packing uses atlas UV units internally: the atlas spans 0–1 and each tile is 0.2 wide/high. Tile Padding is minimum edge clearance; Island Padding is the minimum inter-island gap, counted once between islands or rows. Mixed sizes may leave larger gaps. Invalid packing cancels the entire operation with an “Insufficient tile space” warning, preserving all UVs.

## Version 2.7.7

- Pack UV islands in rows from the padded upper-left corner of each tile, with one uniform scale per tile.
- Validate the whole layout before editing UVs. Distribution reports island, tile, overlap and out-of-bounds counts.
- Support pixel padding with preset or custom atlas resolution alongside legacy UV padding.
- Packing regression suite passed through Flue on Blender 5.2.3 LTS and Blender 5.3.0 Beta and Release Candidate.

## Version 2.7.8

- Enter padding as a percentage of one tile's width. Tile Padding defaults to 1% per edge and Island Padding to 0.5%. Pixels mode remains available, and previously saved padding values retain their distances.
- Validate UVs at Blender's storage precision before editing any mesh. If packing fails, the warning identifies the tile and its settings.
- Verified the registered distribution operator and exact multi-object Undo in Blender 5.3.0.
