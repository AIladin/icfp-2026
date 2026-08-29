//! The seeded generator the whole search shares. Deterministic by repo norm: same seed, same
//! design, same program — a packed grid nobody can reproduce is a grid nobody can debug.

use littleman::ephemeral::xorshift;

pub struct Rng(u64);

impl Rng {
    pub fn new(seed: u64) -> Self {
        Self(seed | 1)
    }

    pub fn next(&mut self) -> u64 {
        self.0 = xorshift(self.0);
        self.0
    }

    /// Uniform in `0..bound` (`0` for an empty bound).
    pub fn below(&mut self, bound: usize) -> usize {
        (self.next() % bound.max(1) as u64) as usize
    }

    /// Non-zero offset in `-spread..=spread`.
    pub fn offset(&mut self, spread: i32) -> i32 {
        let magnitude = self.below(spread.max(1) as usize) as i32 + 1;
        if self.next() % 2 == 0 { magnitude } else { -magnitude }
    }

    pub fn chance(&mut self, percent: u64) -> bool {
        self.next() % 100 < percent
    }

    /// Uniform in `0.0..1.0`, for the Metropolis test.
    pub fn unit(&mut self) -> f64 {
        (self.next() % 1_000_000) as f64 / 1_000_000.0
    }
}
