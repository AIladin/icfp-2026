import prog2 as p

bad = 0
tmax = 0
for x0 in range(32):
    for y0 in range(24):
        for x1 in range(32):
            for y1 in range(24):
                q, t = p.run_case(x0, y0, x1, y1)
                tmax = max(tmax, t)
                mx, dm, tok, dq, mn = q
                px = []
                for i in range(mx + 1):
                    assert tok != 0
                    px.append(tok & 1023)
                    if i < mx:
                        tok += dq if tok >= 0 else dm
                if px != p.reference(x0, y0, x1, y1):
                    bad += 1
                    if bad < 3:
                        print("MISMATCH", (x0, y0, x1, y1))
print("mismatches:", bad, "max ticks:", tmax)
