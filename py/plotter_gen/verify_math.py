"""Verify the unified single-test Bresenham decomposition against the spec pseudocode."""

W = 32


def reference(x0, y0, x1, y1):
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    px = []
    while True:
        px.append(W * y0 + x0)
        if x0 == x1 and y0 == y1:
            return px
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def mine(x0, y0, x1, y1):
    dxv = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    ay = abs(y1 - y0)
    sy32 = 32 if y0 < y1 else -32
    addr0 = W * y0 + x0
    if dxv >= ay:  # x-dominant
        mn, mx, step_m, step_c = ay, dxv, sx, sy32
    else:
        mn, mx, step_m, step_c = dxv, ay, sy32, sx
    E = 2048 * mn
    F = 2048 * mx
    Wc = 1024 * mx
    dm = E + step_m
    dd = E - F + step_m + step_c
    npix = mx + 1
    token = E - Wc + addr0
    out = []
    for _ in range(npix):
        out.append(token % 1024)
        token += dd if token >= 0 else dm
    return out


bad = 0
for x0 in range(32):
    for y0 in range(24):
        for x1 in range(32):
            for y1 in range(24):
                r = reference(x0, y0, x1, y1)
                m = mine(x0, y0, x1, y1)
                if r != m:
                    bad += 1
                    if bad < 6:
                        print("MISMATCH", (x0, y0, x1, y1), r, m)
print("mismatches:", bad)
