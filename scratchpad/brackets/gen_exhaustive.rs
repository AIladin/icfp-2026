use std::io::{self, Write};

const CHARS: [(i64, bool, u8); 6] = [
    (40, true, 0), (41, false, 0),
    (91, true, 1), (93, false, 1),
    (123, true, 2), (125, false, 2),
];

fn expected(xs: &[usize]) -> usize {
    let mut stack = Vec::new();
    for (i, &x) in xs.iter().enumerate() {
        let (_, open, kind) = CHARS[x];
        if open {
            stack.push(kind);
        } else if stack.pop() != Some(kind) {
            return i + 1;
        }
    }
    if stack.is_empty() { 0 } else { xs.len() + 1 }
}

fn emit(out: &mut impl Write, xs: &[usize], first: &mut bool) -> io::Result<()> {
    if !*first { writeln!(out, ",")?; }
    *first = false;
    write!(out, "{{\"name\":\"n{}-", xs.len())?;
    for &x in xs { write!(out, "{}", x)?; }
    write!(out, "\",\"rounds\":[{{\"in\":[\"{}\"", xs.len())?;
    for &x in xs { write!(out, ",\"{}\"", CHARS[x].0)?; }
    write!(out, "],\"out\":[\"{}\"]}}]}}", expected(xs))
}

fn enumerate(out: &mut impl Write, xs: &mut [usize], at: usize, first: &mut bool) -> io::Result<()> {
    if at == xs.len() { return emit(out, xs, first); }
    for x in 0..6 {
        xs[at] = x;
        enumerate(out, xs, at + 1, first)?;
    }
    Ok(())
}

fn main() -> io::Result<()> {
    let max_n = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(5);
    let stdout = io::stdout();
    let mut out = io::BufWriter::new(stdout.lock());
    writeln!(out, "[")?;
    let mut first = true;
    for n in 0..=max_n { enumerate(&mut out, &mut vec![0; n], 0, &mut first)?; }
    writeln!(out, "\n]")
}
