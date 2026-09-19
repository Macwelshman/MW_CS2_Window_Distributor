# MW CS2 Window Distributor
Version 2.7.6 | Macwelshman | Blender 5.2 or later

## Prepare and select
1. Unwrap the window mesh and check that the window faces have usable UVs.
2. Enter Edit Mode and open UV Editor > Sidebar > MW CS2 Win Dist.
3. With UV Sync Selection off, select every UV vertex of each face you want to distribute. With sync on, select the mesh faces instead.
4. Use Orientate UVs before distribution when the windows need world-aligned orientation.
5. Choose Residential or Non-Residential and enable the required window categories.
6. Click Distribute. Only selected faces are moved; unselected connected faces remain unchanged.

## Make separate passes
First select the windows to receive curtains. In Residential mode enable Curtains (Open), Curtains (Closed), or both, and disable Blank. Click Distribute.

Deselect all UVs, then select only the few windows that should be blank. Disable both curtain options, enable Blank, and click Distribute again. The other windows keep their UV placement.

Select complete UV faces or islands, rather than isolated UV vertices or edges. An empty UV selection cancels distribution without changing the UVs. Avoid selecting only part of a face.

## Installation and updates
Install the release ZIP using Blender's Install from Disk command in Preferences > Get Extensions. Alternatively, add the MW repository below and install the extension from it. Repository installations can use Check for Updates.

https://raw.githubusercontent.com/Macwelshman/MW-Blender-Extensions/main/index.json

After manually replacing an installed source file, restart Blender. The installed version should be 2.7.6.

---

# Window categories
Tile numbers run from 1 to 25, left to right and top to bottom across the 5 x 5 atlas. Multiple enabled categories combine their tile sets.

## Residential
- Curtains (Open): 3, 9, 11, 15, 17, 23.
- Curtains (Closed): 4, 6, 10, 12, 18, 24.
- Blank: 1, 2, 5, 7, 8, 13, 14, 16, 19, 20, 21, 22, 25.

## Non-Residential
- Blinds (Vertical): 3, 9, 11, 15, 17, 23.
- Blinds (Open): 1, 5, 7, 13, 19, 21, 25.
- Blinds (Closed): 4, 6, 10, 12, 18, 24.
- Blank: 2, 8, 14, 16, 20, 22.

## Exclude Always On/Off
This control is available in both modes. Enable it to exclude tiles 1 and 25 from any selected category. Disable it to allow those tiles where the category includes them. It does not change the remaining category assignments.

## Choose at least one category
Always enable the categories you want before clicking Distribute. Selecting a new category does not automatically turn off the others. For a Blank-only pass, explicitly disable the curtain or blind categories.

---

# Packing and orientation
## Packing controls
- Tile Padding: adds clearance inside each tile boundary.
- Island Padding: adds clearance between allocated cells within a tile.
- Allow Upscale: permits islands to grow to fill their cells.
- Randomize Distribution: shuffles island assignment using Random Seed. The same selection and seed repeat the same arrangement; change the seed for a different arrangement.

Distribution is repeatable by default. Within each occupied tile, islands use a common uniform scale and are centred in their allocated cells. Cells are filled from the top-left across rows. Aspect ratios are preserved, but scale can differ between tiles.

Use modest padding values. Excessive padding or many islands in one tile can leave insufficient usable space. Inspect the result for tile clearance and overlaps before export.

## Orientate UVs
Orientate UVs processes selected islands across all mesh objects in Edit Mode that have UV maps, using each object's world-space surface orientation. Object rotation and non-zero scale can remain unapplied. The combined result reports rotated, already aligned and skipped islands. Objects with zero scale are reported while valid objects continue. Conflicting edge directions, unusable geometry and zero-scale transforms may prevent orientation.

Orient before distributing: rotating after packing can move UVs outside the tile. Curved or unusual window surfaces may need manual adjustment. Orientation works on whole islands touched by selected faces; selected-only distribution has a stricter face boundary.

## Troubleshooting
- No UV islands selected: check Edit Mode, UV Sync Selection and selection of complete UV faces.
- Wrong window type: verify the mode and turn off unwanted categories.
- Tiles 1 and 25 missing: check Exclude Always On/Off.
- Windows too small: consider Allow Upscale, lower padding or more enabled categories.
- Arrangement does not change: enable Randomize Distribution and change Random Seed.
- Multiple objects: enter Edit Mode with the required mesh objects, then select the UVs on each and run Orientate UVs before Distribute.

Both operators support Undo. Keep a saved copy and inspect the atlas placement and in-game result before final export.

This independent community add-on is not affiliated with Iceflake Studios or Paradox Interactive.
