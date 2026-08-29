//! The program text as a rectangular character grid.
//!
//! > Short source lines are padded with spaces to the longest line's width.
//! > — language-reference#Odds and ends

/// A padded grid of bytes. The language is ASCII, so a byte is a cell.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Grid {
    rows: Vec<Vec<u8>>,
    width: i32,
    height: i32,
}

impl Grid {
    pub fn parse(source: &str) -> Self {
        let replaced = source.replace('\t', " ");
        let mut lines: Vec<&str> = replaced.split('\n').collect();
        // A trailing newline is an editor artefact, not a row of the program.
        while lines.last().is_some_and(|line| line.trim().is_empty()) {
            lines.pop();
        }
        let width = lines.iter().map(|line| line.len()).max().unwrap_or(0);
        let rows: Vec<Vec<u8>> = lines
            .iter()
            .map(|line| {
                let mut row = line.as_bytes().to_vec();
                row.resize(width, b' ');
                row
            })
            .collect();
        let height = rows.len();
        Self { rows, width: width as i32, height: height as i32 }
    }

    pub fn width(&self) -> i32 {
        self.width
    }

    pub fn height(&self) -> i32 {
        self.height
    }

    /// The character at a cell; space outside the grid, so the edge needs no special case.
    pub fn at(&self, x: i32, y: i32) -> u8 {
        if y < 0 || y >= self.height || x < 0 || x >= self.width {
            return b' ';
        }
        self.rows[y as usize][x as usize]
    }

    pub fn row(&self, y: i32) -> &[u8] {
        &self.rows[y as usize]
    }

    /// Bounding box `(x0, y0, x1, y1)` of non-space content; `(0, 0, -1, -1)` when empty.
    pub fn content_box(&self) -> (i32, i32, i32, i32) {
        let (mut x0, mut x1) = (self.width, -1);
        let (mut y0, mut y1) = (self.height, -1);
        // Whitespace, not just spaces: Python's `strip()` also eats a stray `\r` from a CRLF file,
        // and the footprint is the score's size term — it must not depend on line endings.
        for (y, row) in self.rows.iter().enumerate() {
            let first = row.iter().position(|c| !c.is_ascii_whitespace());
            let Some(first) = first else { continue };
            let last = row.iter().rposition(|c| !c.is_ascii_whitespace()).unwrap_or(first);
            let y = y as i32;
            y0 = y0.min(y);
            y1 = y1.max(y);
            x0 = x0.min(first as i32);
            x1 = x1.max(last as i32);
        }
        if y1 < 0 { (0, 0, -1, -1) } else { (x0, y0, x1, y1) }
    }

    /// `(width, height)` of the content bounding box — the term the score squares.
    pub fn footprint(&self) -> (i32, i32) {
        let (x0, y0, x1, y1) = self.content_box();
        ((x1 - x0 + 1).max(0), (y1 - y0 + 1).max(0))
    }

    /// A small window around a cell, for error messages.
    pub fn excerpt(&self, x: i32, y: i32, radius: i32) -> String {
        let mut lines = Vec::new();
        for row_y in (y - radius).max(0)..(y + radius + 1).min(self.height) {
            let marker = if row_y == y { '>' } else { ' ' };
            let text = String::from_utf8_lossy(self.row(row_y));
            lines.push(format!("{marker}{row_y:>4} |{text}"));
        }
        lines.push(format!("      {}^ ({x},{y})", " ".repeat(x.max(0) as usize)));
        lines.join("\n")
    }
}
