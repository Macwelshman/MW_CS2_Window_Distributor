"""Pure Python: python3 -B tests/check_packing_math.py (no Blender imports)."""
import ast
import math
import struct
from fractions import Fraction
from pathlib import Path
source = ast.parse((Path(__file__).resolve().parents[1] / '__init__.py').read_text())
namespace = {'math': math, 'struct': struct, 'Fraction': Fraction}
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef)
    and n.name in ('_plan_tile', '_validate_padding', '_effective_padding', '_validate_tile_layout',
                   '_inward_float32')], type_ignores=[]), 'packing', 'exec'), namespace)
plan = namespace['_plan_tile']

def check(sizes, tp, ip, upscale):
    data = [{'size': size} for size in sizes]
    result = plan(data, (.4, .6), .2, .2, tp, ip, upscale)
    left, top, bottom = .4 + tp, .8 - tp, .8 - tp
    for i, (scale, offset, box) in enumerate(result):
        assert scale > 0 and (upscale or scale <= 1)
        assert scale == result[0][0]
        if i and not math.isclose(box[3], top, abs_tol=1e-9):
            left, top, bottom = .4 + tp, bottom - ip, bottom - ip
        assert math.isclose(box[0], left, abs_tol=1e-9)
        assert math.isclose(box[3], top, abs_tol=1e-9)
        left, bottom = box[2] + ip, min(bottom, box[1])
        assert box[0] >= .4+tp-1e-9 and box[2] <= .6-tp+1e-9
        assert box[1] >= .6+tp-1e-9 and box[3] <= .8-tp+1e-9
        for axis in (0,1):
            assert math.isclose(box[axis+2]-box[axis], sizes[i][axis]*scale)
        for _, _, other in result[:i]:
            assert any((box[a] >= other[a+2]+ip-1e-9 or other[a] >= box[a+2]+ip-1e-9) for a in (0,1))

for n in (1,2,4,9,24,216):
    for tp, ip in ((0,0),(0,.001),(.05,.05),(0,.05),(.05,0)):
        for upscale in (False,True):
            if ip and (math.ceil((.2 - 2*tp)/ip) ** 2 < n):
                continue
            check([((.03,.15) if i%2 else (.12,.007)) for i in range(n)],tp,ip,upscale)
def pack(sizes, edge=0, gap=0, upscale=True):
    return plan([{'size': size} for size in sizes], (0, 0), .2, .2, edge, gap, upscale)

assert len(pack([(.01, .02)], .05, .05)) == 1
mixed = pack([(.03, .05), (.06, .025), (.09, .02)], .01, .01, False)
assert mixed[0][0] == 1
assert math.isclose(mixed[1][2][0], .05)
assert math.isclose(mixed[2][2][3], .13)
try:
    pack([(1, 1)] * 5, .05, .05)
except ValueError:
    pass
else:
    raise AssertionError("Five islands cannot fit in four padded positions")
for bad in ((0,1),(float('nan'),1),(1,float('inf'))):
    try: plan([{'size':bad}],(0,0),.2,.2,0,0,False)
    except ValueError: pass
    else: raise AssertionError(bad)
print('PACKING_MATH_PASS: mixed-size cases, bounds, top-left, separation, scale and invalid sizes')

from types import SimpleNamespace

for resolution in (512, 1024, 2048, 4096, 1000):
    props = SimpleNamespace(padding_units='PIXELS',
                            atlas_resolution='CUSTOM' if resolution == 1000 else str(resolution),
                            custom_resolution=1000, tile_padding_px=4, island_padding_px=4)
    effective = namespace['_effective_padding']
    assert effective(props) == (4 / resolution, 4 / resolution)
    sizes = [(1, 1), (.2, 1), (1, .2)]
    check(sizes, *effective(props), True)
    props.tile_padding_px = props.island_padding_px = 0
    check(sizes, *effective(props), True)
    props.tile_padding_px = (resolution - 1) // 10
    assert plan([{'size': (1, 1)}], (0, 0), .2, .2, *effective(props), True)
    props.tile_padding_px += 1
    try:
        plan([{'size': (1, 1)}], (0, 0), .2, .2, *effective(props), True)
    except ValueError as exc:
        assert "no usable tile area" in str(exc)
    else:
        raise AssertionError("Accepted padding with no usable tile area")
    props.padding_units = 'UV'
    props.tile_padding, props.island_padding = .01, .001
    assert effective(props) == (.01, .001)

print("Pixel padding: presets, custom resolution, zero, tile limit and legacy UV passed")

validate = namespace['_validate_tile_layout']
assert validate([(0, 0, .05, .05), (.06, 0, .1, .05)], (0, 0, .2, .2), .01) == (0, 0, 0)
assert validate([(0, 0, .05, .05), (.055, 0, .1, .05)], (0, 0, .2, .2), .01) == (0, 0, 1)
assert validate([(0, 0, .05, .05), (.04, -.01, .1, .05)], (0, 0, .2, .2), .01) == (1, 1, 1)
assert validate([(.4, .8, .6000000238418579, 1)], (.4, .8, .6, 1), 0) == (0, 1, 0)
assert validate([(0, 0, .05, .05), (.05 - 1e-8, 0, .1, .05)], (0, 0, .2, .2), 0) == (1, 0, 1)
print("Layout diagnostics: overlap, bounds and short spacing counted separately")


def rejects(reason, *args, **kwargs):
    try:
        plan(*args, **kwargs)
    except ValueError as exc:
        assert reason in str(exc), exc
    else:
        raise AssertionError(f"Expected rejection: {reason}")


square = {'size': (1, 1)}
assert len(plan([square] * 4, (.4, .8), .2, .2, .05, .05, True, stored_uvs=True)) == 4
rejects("required gaps alone", [square] * 36, (.4, .8), .2, .2, 0, .05, True)
rejects("no usable tile area", [square], (0, 0), .2, .2, .1, 0, True)
rejects("no usable tile area", [square], (0, 0), math.nan, .2, 0, 0, True)
rejects("non-finite tile coordinates", [square], (math.inf, 0), .2, .2, 0, 0, True)
rejects("would collapse", [{'size': (1, 1e-30)}], (.4, .8), .2, .2, 0, 0, True)
_, _, box = plan([square], (.4, .8), .2, .2, 0, 0, True, stored_uvs=True)[0]
assert struct.unpack(">f", struct.pack(">f", box[2]))[0] <= .6
print("Strict stored UV bounds, impossible spacing and precision collapse passed")
