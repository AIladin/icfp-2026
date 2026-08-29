"""Validate the room-level decomposition: P (always-add dm) / Q (cross-add dq), counters mx / mn."""

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


def machine(x0, y0, x1, y1):
    # --- setup ---
    ex = x1 - x0
    d = ex if ex > 0 else -ex
    sx = 1 if ex > 0 else -1
    ey = y1 - y0
    a = ey if ey > 0 else -ey
    sy32 = 32 if ey > 0 else -32
    addr0 = 32 * y0 + x0
    e = d - a
    if e >= 0:
        Dv = e
        step_m = sx
    else:
        Dv = -e
        step_m = sy32
    S = d + a
    mn = (S - Dv) >> 1
    mx = (S + Dv) >> 1
    U = mn << 11
    dm = U + step_m
    dq = U - (mx << 11) + sx + sy32
    tok = U - (mx << 10) + addr0
    # --- ring ---
    out = []
    crosses = 0
    for _ in range(mx + 1):
        out.append(tok & 1023)
        if _ == mx:
            break
        if tok >= 0:
            tok = tok + dq  # room Q holds dq = dm + G
            crosses += 1
        else:
            tok = tok + dm
    assert crosses == mn, (x0, y0, x1, y1, crosses, mn)
    return out


bad = 0
for x0 in range(32):
    for y0 in range(24):
        for x1 in range(32):
            for y1 in range(24):
                r = reference(x0, y0, x1, y1)
                m = machine(x0, y0, x1, y1)
                if r != m:
                    bad += 1
                    if bad < 4:
                        print("MISMATCH", (x0, y0, x1, y1), r, m)
print("mismatches:", bad)
