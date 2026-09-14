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
- Includes compatibility handling for Blender 5.2 UV selection attributes.
- Distribution and orientation operations support Undo.

## Requirements

- **Blender 5.2 or later**
- A mesh with an existing UV map
- Window UV islands prepared for placement within the CS2 window atlas

The current source version is **2.7.5**.

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

Select the complete UV island in the UV Editor. All UV vertices belonging to each face should be selected.

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

Enable one or more groups to combine their tile sets. Tile numbering runs left to right, starting at the top-left. **Exclude Always On/Off** removes tiles 1 and 25 in either mode when enabled.

## Controls

### Exclude Always On/Off

Excludes the first and last atlas tiles from distribution. These correspond to the two edge tiles reserved by the add-on as always-on/always-off variants.

### Tile Padding

Adds space between the UV islands and the outer edge of each atlas tile.

- Default: `0.0`
- Range: `0.0–0.05`

Increase this slightly if texture filtering or mipmapping causes neighbouring tiles to bleed into the selected window.

### Island Padding

Adds spacing between multiple islands packed into the same atlas tile.

- Default: `0.001`
- Range: `0.0–0.05`

Very high values can leave too little room for the UV islands.

### Allow Upscale

Allows islands to grow to fill their calculated grid cells.

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

The add-on can distribute islands from several objects in one operation.

1. Select all required mesh objects.
2. Enter multi-object Edit Mode.
3. Select the required faces or UV islands on each object.
4. Click **Distribute**.

The add-on gathers the selected islands from all editable mesh objects, distributes them as one combined set, and updates each object afterwards.

## Packing behaviour

Each atlas tile is divided into a square-like grid based on the number of islands assigned to it.

The add-on then:

1. Calculates the available cell size after padding.
2. Finds one uniform scale that allows every island in that tile to fit.
3. Preserves the aspect ratio and relative proportions of the islands.
4. Centres each island inside its allocated cell.

Because one scale is used per tile, smaller islands may not fill their cells as much as larger islands in the same tile.

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

The version installed from the current source should appear as **2.7.5**.

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
    └── mw_cs2_window_distributor-2.7.5.zip
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
