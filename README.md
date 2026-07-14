# MW CS2 Window Distributor

A Blender UV Editor add-on for assigning selected UV islands across the 5 x 5 Counter-Strike 2 window texture grid.

## Features

- Commercial and residential tile presets.
- Distributes selected UV islands across selected tile types.
- Supports multiple mesh objects in Edit Mode.
- Optional deterministic random distribution with a reusable seed.
- Adjustable tile and island padding.
- Optional uniform upscaling per tile, preserving relative island scale.
- World-orients selected UV islands from their mesh normals.

## Installation

1. Download the repository as a ZIP, or package the `MW_CS2_Window_Distributor` folder as a ZIP.
2. In Blender, open **Edit > Preferences > Add-ons > Install** and select the ZIP.
3. Enable **MW CS2 Window Distributor**.
4. In the UV Editor sidebar, open the **MW CS2 Win Dist** tab.

## Usage

1. Select one or more mesh objects and enter Edit Mode.
2. Select the UV islands to distribute. With UV Sync Selection off, select all UVs in each island.
3. Choose Commercial or Residential mode and the desired window types.
4. Optionally tune packing settings, then choose **Distribute**.

Leave **Randomize Distribution** off for repeatable results. When it is on, the same seed produces the same tile assignment for the same selected islands.

## Compatibility

Blender 3.0 and later.

## Development

The add-on source is intentionally kept in `__init__.py` for easy Blender installation. Run a syntax check with:

```sh
python3 -B -c "import ast, pathlib; ast.parse(pathlib.Path('__init__.py').read_text())"
```
