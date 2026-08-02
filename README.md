# MW CS2 Window Distributor

A Blender UV Editor add-on for distributing window UV islands across the **5 × 5 window texture atlas used by Cities: Skylines II**.

The add-on places selected UV islands into predefined commercial or residential window tiles, keeps distribution repeatable by default, and provides controls for padding, scaling, randomisation, and world-aligned UV orientation.

## Features

- Distributes selected UV islands across a 5 × 5 CS2 window atlas.
- Commercial and residential window presets.
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

- **Blender 3.0 or later**
- A mesh with an existing UV map
- Window UV islands prepared for placement within the CS2 window atlas

The current source version is **2.7.2**.

## Installation

### Install the packaged add-on

1. Download the add-on ZIP from the repository's releases or `dist` folder.
2. Open Blender.
3. Go to **Edit → Preferences → Add-ons**.
4. Click the menu in the upper-right corner and choose **Install from Disk**.
5. Select the add-on ZIP.
6. Enable **MW CS2 Window Distributor** if Blender does not enable it automatically.

Do not extract the installation ZIP before installing it through Blender.

### Install from the source folder

1. Place `__init__.py` inside a folder named `MW_CS2_Window_Distributor`.
2. Compress that folder as a ZIP.
3. Install the ZIP through **Edit → Preferences → Add-ons → Install from Disk**.

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
5. Choose **Commercial** or **Residential** mode.
6. Enable one or more window categories.
7. Adjust the packing options when needed.
8. Click **Distribute**.

The selected islands will be assigned across the enabled atlas tiles. When more islands are selected than there are available tiles, the add-on cycles through the selected tiles and packs multiple islands into each tile.

## Selecting UV islands

The add-on works with **UV Sync Selection** either enabled or disabled.

### UV Sync Selection enabled

Select the relevant mesh faces in Edit Mode. Their UV islands will be processed.

### UV Sync Selection disabled

Select the complete UV island in the UV Editor. All UV vertices belonging to each face should be selected.

If Blender reports **Select one or more UV islands**, check that the full islands are selected rather than only individual UV vertices or edges.

## Distribution modes

### Commercial

Commercial mode provides four tile groups:

- **Blinds (Vertical)**
- **Blinds (Open)**
- **Blinds (Closed)**
- **Blank**

You can enable several groups together. The add-on distributes islands across the combined set of corresponding atlas tiles.

### Residential

Residential mode provides:

- **Curtains**
- **Blank**

Enable one or both groups to choose the residential tiles available for distribution.

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
2. Apply the object's rotation and scale when appropriate.
3. Click **Orientate UVs**.
4. Inspect the result in the UV Editor.
5. Click **Distribute** when ready.

The operator evaluates the average world-space normal and weighted edge directions of each selected island. Unusual, curved, or irregular geometry may still require manual adjustment.

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
5. Choose the required commercial or residential window groups.
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

1. Download the newer add-on ZIP.
2. Open **Edit → Preferences → Add-ons**.
3. Disable or remove the old version if necessary.
4. Install the new ZIP through **Install from Disk**.
5. Restart Blender if the old code remains loaded.

The version installed from the current source should appear as **2.7.2**.

## Development

The add-on is contained in a single `__init__.py` file for straightforward Blender installation.

A basic syntax check can be run from the repository root with:

```bash
python3 -B -c "import ast, pathlib; ast.parse(pathlib.Path('__init__.py').read_text())"
```

### Repository structure

```text
MW_CS2_Window_Distributor/
├── __init__.py
├── README.md
└── dist/
    └── MW_CS2_Window_Distributor-2.7.0.zip
```

The packaged ZIP in `dist` may be older than the version declared by the current source. Rebuild the release package before publishing a new release.

## Disclaimer

This is an independent community tool and is not affiliated with or endorsed by **Iceflake Studios** or **Paradox Interactive**.

Cities: Skylines II and its associated names and trademarks belong to their respective owners.
