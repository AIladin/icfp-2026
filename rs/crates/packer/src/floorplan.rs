//! B\*-tree floorplanning: the placement is *derived*, not searched over directly.
//!
//! The free-coordinate placer this replaces stalled for a structural reason. Its state was an x/y
//! per room and its moves were one-cell nudges that had to leave the *whole design* routable, so
//! near a packed layout almost every neighbour overlapped or failed to route and acceptance
//! collapsed. Pulling all fourteen rooms one cell tighter needed fourteen separately-accepted
//! moves, each individually routable — which never happened, and ten parallel chains reached
//! exactly the same plateau as one.
//!
//! A B\*-tree is in 1-1 correspondence with *admissible* placements: ones already compacted so far
//! that nothing can slide further west or north. Every tree packs to one, so overlap is impossible
//! by construction and a single topological move re-compacts everything downstream of it.
//!
//! The catch, and the reason for [`Floorplan::halo`]: our optimum is **not** an admissible
//! placement of the room boxes. Rooms sit apart because pipes run between them, which in box terms
//! is inadmissible — pack them flush and nothing routes at all. So each node is inflated by its
//! routing slack and the *inflated* rectangles pack flush; the gaps between real boxes are the
//! channels. The halo is per-side because slack is asymmetric: a three-wide bus to the east must
//! not buy three cells of dead space on the other three walls, since that lands directly in
//! `max(w, h)`, which is the entire cost.
//!
//! What a B\*-tree cannot do is move one room two cells without re-packing half the design. That
//! is what [`crate::anneal`]'s polish stage is for.

use littleman::model::{Cell, EAST, NORTH, SOUTH, WEST};

use crate::assemble::State;
use crate::design::Design;
use crate::library::{Library, Variant};
use crate::rng::Rng;

/// Absent child / absent parent.
pub const NONE: usize = usize::MAX;

/// Per-side routing slack is clamped here. It is generous because halo is the *only* way this
/// representation can express empty space: [`Floorplan::grid`] uses it to hold rooms on a shared
/// row/column lattice, which needs tens of cells around a small room that shares a row with a tall
/// one. The seeder strips it greedily and the annealer walks it back a cell at a time.
pub const MAX_HALO: i32 = 24;

/// A B\*-tree over `n` slots plus what each slot's room looks like.
///
/// The tree shape is indexed by **slot**; `at[slot]` names the instance sitting there. That
/// indirection is what makes the swap move one line — exchanging two rooms' positions is
/// exchanging two labels, with no rewiring at all.
///
/// Packing: the **left** child sits immediately EAST of its parent (`x = parent.x + parent.width`),
/// the **right** child directly SOUTH at the same `x`. Both take their `y` from the contour of
/// everything placed before them in preorder.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Floorplan {
    left: Vec<usize>,
    right: Vec<usize>,
    parent: Vec<usize>,
    root: usize,
    at: Vec<usize>,
    /// By instance, matching [`State::variant`].
    pub variant: Vec<usize>,
    /// By instance: extra clearance beyond the variant's `pad`, indexed by direction.
    pub halo: Vec<[i32; 4]>,
    /// The largest value search may restore on each side. Lattice alignment can create halos wider
    /// than [`MAX_HALO`]; remember that inherited slack so annealing can tighten and later restore
    /// it without allowing unbounded expansion.
    halo_cap: Vec<[i32; 4]>,
}

impl Floorplan {
    /// A right-chain over `order` — every room south of the last, which is legal but tall. The
    /// seeder builds something better; this is the floor the tree ops are tested against.
    pub fn chain(order: &[usize], variant: Vec<usize>, halo: i32) -> Self {
        let count = order.len();
        let mut plan = Floorplan {
            left: vec![NONE; count],
            right: vec![NONE; count],
            parent: vec![NONE; count],
            root: 0,
            at: order.to_vec(),
            variant,
            halo: vec![[halo; 4]; count],
            halo_cap: vec![[halo.max(MAX_HALO); 4]; count],
        };
        for slot in 1..count {
            plan.right[slot - 1] = slot;
            plan.parent[slot] = slot - 1;
        }
        plan
    }

    pub fn rooms(&self) -> usize {
        self.at.len()
    }

    /// Build a lattice: `cells[i]` puts instance `i` in a (column, row), every column becomes a
    /// right-chain stacked south, and the next column hangs east off the previous column's head.
    ///
    /// The halo is what makes it a *lattice* rather than fourteen independently-stacked columns.
    /// Every room is inflated to exactly its column's width and its row's height, and a room whose
    /// column skips a row absorbs that row's height into its north halo. So rows line up across
    /// columns and the design gets clean channels running its full width — which is what the old
    /// free-coordinate seeder produced, and, on this pilot, the difference between a seed that
    /// routes and one that does not at any spacing.
    pub fn grid(
        library: &Library,
        design: &Design,
        cells: &[(usize, usize)],
        variant: Vec<usize>,
        gap: i32,
    ) -> Self {
        let count = cells.len();
        let base = |instance: usize| -> (i32, i32) {
            let name = &design.instances[instance].type_name;
            let v = &library.types[name].variants[variant[instance]];
            let span = |a: u8, b: u8| v.pad[a as usize] + v.pad[b as usize];
            (v.width + span(WEST, EAST), v.height + span(NORTH, SOUTH))
        };

        let width_of = cells.iter().map(|c| c.0).max().unwrap_or(0) + 1;
        let height_of = cells.iter().map(|c| c.1).max().unwrap_or(0) + 1;
        let mut column_width = vec![0i32; width_of];
        let mut row_height = vec![0i32; height_of];
        for (instance, &(column, row)) in cells.iter().enumerate() {
            let (width, height) = base(instance);
            column_width[column] = column_width[column].max(width + gap);
            row_height[row] = row_height[row].max(height + gap);
        }

        let mut columns: Vec<Vec<usize>> = vec![Vec::new(); width_of];
        for (instance, &(column, _)) in cells.iter().enumerate() {
            columns[column].push(instance);
        }
        for column in &mut columns {
            column.sort_by_key(|&instance| (cells[instance].1, instance));
        }

        let mut halo = vec![[0i32; 4]; count];
        for (index, column) in columns.iter().enumerate() {
            let mut next_row = 0usize;
            for &instance in column {
                let (width, height) = base(instance);
                let row = cells[instance].1;
                let skipped: i32 = row_height[next_row..row].iter().sum();
                next_row = row + 1;
                // All the spare goes east and south, so every room in a column shares a west wall
                // and every room in a row shares a north wall. Centring instead leaves the channel
                // walls ragged, and a pipe running the length of a ragged channel has to weave.
                halo[instance][EAST as usize] = column_width[index] - width;
                halo[instance][SOUTH as usize] = row_height[row] - height;
                halo[instance][NORTH as usize] = skipped;
            }
        }

        let order: Vec<usize> = columns.iter().flatten().copied().collect();
        let mut plan = Floorplan::chain(&order, variant, 0);
        plan.halo_cap = halo.iter().map(|room| room.map(|side| side.max(MAX_HALO))).collect();
        plan.halo = halo;
        plan.left.iter_mut().for_each(|link| *link = NONE);
        plan.right.iter_mut().for_each(|link| *link = NONE);
        plan.parent.iter_mut().for_each(|link| *link = NONE);

        let mut slot = 0usize;
        let mut previous: Option<usize> = None;
        for column in &columns {
            if column.is_empty() {
                continue;
            }
            let head = slot;
            for _ in column {
                if slot > head {
                    plan.right[slot - 1] = slot;
                    plan.parent[slot] = slot - 1;
                }
                slot += 1;
            }
            // Every room in a column is padded to the same width, so hanging the next column off
            // the head clears the whole column exactly.
            if let Some(anchor) = previous {
                plan.left[anchor] = head;
                plan.parent[head] = anchor;
            }
            previous = Some(head);
        }
        plan
    }

    /// Total slack: what the seeder's greedy strip is trying to drive down.
    pub fn slack(&self) -> i32 {
        self.halo.iter().flatten().sum()
    }

    /// Take `step` cells off every halo that has them. Returns how many sides gave, so a caller
    /// can tell "nothing left to give" from "tightened".
    pub fn shrink_all(&mut self, step: i32) -> usize {
        let mut taken = 0;
        for side in self.halo.iter_mut().flatten() {
            if *side >= step {
                *side -= step;
                taken += 1;
            }
        }
        taken
    }

    /// Adjust one side within the slack envelope established by the seed. Returns whether the
    /// floorplan changed, allowing the search to skip an expensive route call for a capped move.
    pub fn adjust_halo(&mut self, instance: usize, side: usize, step: i32) -> bool {
        let before = self.halo[instance][side];
        self.halo[instance][side] = (before + step).clamp(0, self.halo_cap[instance][side]);
        self.halo[instance][side] != before
    }

    fn variant_of<'a>(&self, library: &'a Library, design: &Design, slot: usize) -> &'a Variant {
        let instance = self.at[slot];
        &library.types[&design.instances[instance].type_name].variants[self.variant[instance]]
    }

    /// The inflated rectangle a slot occupies: the room box plus its pad ring plus its halo.
    fn rect(&self, library: &Library, design: &Design, slot: usize) -> (i32, i32) {
        let variant = self.variant_of(library, design, slot);
        let halo = self.halo[self.at[slot]];
        let span = |a: u8, b: u8| {
            halo[a as usize] + halo[b as usize] + variant.pad[a as usize] + variant.pad[b as usize]
        };
        (variant.width + span(WEST, EAST), variant.height + span(NORTH, SOUTH))
    }

    /// Pack the tree into concrete box origins. Preorder DFS with a skyline contour: `x` is known
    /// when a node is pushed (from its parent), `y` is read off the contour when it is popped, by
    /// which point every node placed before it in preorder has already filled the skyline.
    pub fn realize(&self, library: &Library, design: &Design) -> State {
        let mut pos: Vec<Cell> = vec![(0, 0); self.at.len()];
        let mut sky: Vec<i32> = Vec::new();
        let mut stack = vec![(self.root, 0i32)];
        while let Some((slot, x)) = stack.pop() {
            let (width, height) = self.rect(library, design, slot);
            let top = (x..x + width)
                .map(|column| sky.get(column as usize).copied().unwrap_or(0))
                .max()
                .unwrap_or(0);
            if sky.len() < (x + width) as usize {
                sky.resize((x + width) as usize, 0);
            }
            sky[x as usize..(x + width) as usize].fill(top + height);

            let variant = self.variant_of(library, design, slot);
            let halo = self.halo[self.at[slot]];
            pos[self.at[slot]] = (
                x + variant.pad[WEST as usize] + halo[WEST as usize],
                top + variant.pad[NORTH as usize] + halo[NORTH as usize],
            );

            // Right first so left pops first: the left subtree must fill the contour before the
            // right child, which shares its parent's x, reads it.
            if self.right[slot] != NONE {
                stack.push((self.right[slot], x));
            }
            if self.left[slot] != NONE {
                stack.push((self.left[slot], x + width));
            }
        }
        State { pos, variant: self.variant.clone() }
    }

    // ------------------------------------------------------------------------------- tree edits

    /// Exchange two rooms' positions. One line, because the shape is indexed by slot and the room
    /// is only a label on it.
    pub fn swap(&mut self, a: usize, b: usize) {
        self.at.swap(a, b);
    }

    /// Detach a slot: rotate it down until it is a leaf, then unlink. Returns false when the slot
    /// is the only node there is, which nothing can usefully relocate.
    pub fn detach(&mut self, slot: usize, rng: &mut Rng) -> bool {
        if self.at.len() < 2 {
            return false;
        }
        while self.left[slot] != NONE || self.right[slot] != NONE {
            let (left, right) = (self.left[slot], self.right[slot]);
            let child = match (left, right) {
                (NONE, other) => other,
                (other, NONE) => other,
                (left, right) => {
                    if rng.next() % 2 == 0 {
                        left
                    } else {
                        right
                    }
                }
            };
            self.lift(child);
        }
        let parent = self.parent[slot];
        if parent == NONE {
            return false; // a lone leaf that is also the root: the tree is one node.
        }
        if self.left[parent] == slot {
            self.left[parent] = NONE;
        } else {
            self.right[parent] = NONE;
        }
        self.parent[slot] = NONE;
        true
    }

    /// Swap a child with its parent, so the parent moves one level down. Depth strictly increases
    /// for the parent, which is what makes [`detach`](Self::detach) terminate.
    fn lift(&mut self, child: usize) {
        let node = self.parent[child];
        let above = self.parent[node];
        let node_was_left = above != NONE && self.left[above] == node;
        let child_was_left = self.left[node] == child;
        let sibling = if child_was_left { self.right[node] } else { self.left[node] };
        let (grand_left, grand_right) = (self.left[child], self.right[child]);

        self.parent[child] = above;
        if above == NONE {
            self.root = child;
        } else if node_was_left {
            self.left[above] = child;
        } else {
            self.right[above] = child;
        }

        if child_was_left {
            self.left[child] = node;
            self.right[child] = sibling;
        } else {
            self.right[child] = node;
            self.left[child] = sibling;
        }
        self.parent[node] = child;
        if sibling != NONE {
            self.parent[sibling] = child;
        }

        self.left[node] = grand_left;
        self.right[node] = grand_right;
        for grandchild in [grand_left, grand_right] {
            if grandchild != NONE {
                self.parent[grandchild] = node;
            }
        }
    }

    /// Hang a detached slot under `under`, taking the named side. Any incumbent subtree is pushed
    /// down the same side rather than displaced, so an insert is always legal and never orphans.
    pub fn insert(&mut self, slot: usize, under: usize, left_side: bool) {
        let incumbent = if left_side { self.left[under] } else { self.right[under] };
        self.left[slot] = NONE;
        self.right[slot] = NONE;
        self.parent[slot] = under;
        if left_side {
            self.left[under] = slot;
            self.left[slot] = incumbent;
        } else {
            self.right[under] = slot;
            self.right[slot] = incumbent;
        }
        if incumbent != NONE {
            self.parent[incumbent] = slot;
        }
    }

    /// Detach a slot and re-hang it somewhere else. No-op (returning false) when there is nowhere
    /// else to put it.
    pub fn relocate(&mut self, slot: usize, rng: &mut Rng) -> bool {
        if !self.detach(slot, rng) {
            return false;
        }
        // A detached slot is a leaf with no links left, so every other slot is a legal host — and
        // `detach` only succeeds when there is at least one.
        let count = self.at.len();
        let mut under = rng.below(count);
        while under == slot {
            under = (under + 1) % count;
        }
        self.insert(slot, under, rng.next() % 2 == 0);
        true
    }

    /// Structural invariants, for the tests and for a debug assertion in the search.
    #[cfg(test)]
    fn check(&self) {
        let count = self.at.len();
        let mut sorted = self.at.clone();
        sorted.sort_unstable();
        assert_eq!(sorted, (0..count).collect::<Vec<_>>(), "at is not a permutation");
        assert_eq!(self.parent[self.root], NONE, "the root has a parent");
        let mut seen = vec![false; count];
        let mut stack = vec![self.root];
        while let Some(slot) = stack.pop() {
            assert!(!seen[slot], "slot {slot} is reachable twice");
            seen[slot] = true;
            for (child, is_left) in [(self.left[slot], true), (self.right[slot], false)] {
                if child == NONE {
                    continue;
                }
                assert_eq!(self.parent[child], slot, "child {child} disowns its parent");
                let _ = is_left;
                stack.push(child);
            }
        }
        assert!(seen.iter().all(|&hit| hit), "the tree does not reach every slot");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A tree of unit-ish rectangles, so the packing can be checked without a rooms library.
    struct Sizes(Vec<(i32, i32)>);

    /// Mirror of [`Floorplan::realize`] over explicit sizes — the geometry under test, with the
    /// library lookup taken out of the way.
    fn pack(plan: &Floorplan, sizes: &Sizes) -> Vec<(i32, i32, i32, i32)> {
        let mut rects = vec![(0, 0, 0, 0); plan.at.len()];
        let mut sky: Vec<i32> = Vec::new();
        let mut stack = vec![(plan.root, 0i32)];
        while let Some((slot, x)) = stack.pop() {
            let (width, height) = sizes.0[plan.at[slot]];
            let top = (x..x + width)
                .map(|column| sky.get(column as usize).copied().unwrap_or(0))
                .max()
                .unwrap_or(0);
            if sky.len() < (x + width) as usize {
                sky.resize((x + width) as usize, 0);
            }
            sky[x as usize..(x + width) as usize].fill(top + height);
            rects[plan.at[slot]] = (x, top, x + width, top + height);
            if plan.right[slot] != NONE {
                stack.push((plan.right[slot], x));
            }
            if plan.left[slot] != NONE {
                stack.push((plan.left[slot], x + width));
            }
        }
        rects
    }

    fn sizes(count: usize, rng: &mut Rng) -> Sizes {
        Sizes((0..count).map(|_| (rng.below(9) as i32 + 2, rng.below(9) as i32 + 2)).collect())
    }

    fn overlapping(rects: &[(i32, i32, i32, i32)]) -> Option<(usize, usize)> {
        for (i, a) in rects.iter().enumerate() {
            for (j, b) in rects.iter().enumerate().skip(i + 1) {
                if a.0 < b.2 && b.0 < a.2 && a.1 < b.3 && b.1 < a.3 {
                    return Some((i, j));
                }
            }
        }
        None
    }

    fn plan_of(count: usize) -> Floorplan {
        let order: Vec<usize> = (0..count).collect();
        Floorplan::chain(&order, vec![0; count], 0)
    }

    #[test]
    fn a_chain_packs_without_overlap() {
        let mut rng = Rng::new(1);
        let plan = plan_of(8);
        let rects = pack(&plan, &sizes(8, &mut rng));
        assert_eq!(overlapping(&rects), None);
    }

    /// The property that makes the whole representation worth having: whatever the search does to
    /// the tree, the placement it packs to is legal.
    #[test]
    fn random_trees_never_overlap() {
        for seed in 1..60u64 {
            let mut rng = Rng::new(seed.wrapping_mul(0x9E37_79B9_7F4A_7C15) | 1);
            let count = 4 + rng.below(12);
            let mut plan = plan_of(count);
            let sizes = sizes(count, &mut rng);
            for _ in 0..80 {
                match rng.below(3) {
                    0 => {
                        let slot = rng.below(count);
                        plan.relocate(slot, &mut rng);
                    }
                    1 => {
                        let (a, b) = (rng.below(count), rng.below(count));
                        plan.swap(a, b);
                    }
                    _ => {
                        let slot = rng.below(count);
                        plan.detach(slot, &mut rng);
                        plan.insert(slot, plan.root, rng.next() % 2 == 0);
                    }
                }
                plan.check();
                let rects = pack(&plan, &sizes);
                assert_eq!(overlapping(&rects), None, "seed {seed}");
            }
        }
    }

    #[test]
    fn inherited_oversized_halo_can_be_tightened_and_restored() {
        let mut plan = Floorplan::chain(&[0], vec![0], 40);
        assert!(plan.adjust_halo(0, EAST as usize, -1));
        assert_eq!(plan.halo[0][EAST as usize], 39);
        assert!(plan.adjust_halo(0, EAST as usize, 1));
        assert_eq!(plan.halo[0][EAST as usize], 40);
        assert!(!plan.adjust_halo(0, EAST as usize, 1));
    }

    #[test]
    fn search_created_halo_stays_bounded() {
        let mut plan = Floorplan::chain(&[0], vec![0], 0);
        assert!(!plan.adjust_halo(0, NORTH as usize, -1));
        for _ in 0..MAX_HALO {
            assert!(plan.adjust_halo(0, NORTH as usize, 1));
        }
        assert!(!plan.adjust_halo(0, NORTH as usize, 1));
        assert_eq!(plan.halo[0][NORTH as usize], MAX_HALO);
    }

    #[test]
    fn packing_is_deterministic() {
        let mut rng = Rng::new(7);
        let count = 10;
        let mut plan = plan_of(count);
        let sizes = sizes(count, &mut rng);
        for _ in 0..25 {
            plan.relocate(rng.below(count), &mut rng);
        }
        assert_eq!(pack(&plan, &sizes), pack(&plan, &sizes));
    }

    /// Compaction is the point: a right-chain of 10 boxes is tall, and relocating them into left
    /// children must make the arrangement wider and shorter, not merely different.
    #[test]
    fn left_children_grow_east() {
        let count = 6;
        let sizes = Sizes(vec![(4, 3); count]);
        let mut chain = plan_of(count);
        let tall = pack(&chain, &sizes).iter().map(|r| r.3).max().unwrap();
        for slot in 1..count {
            chain.detach(slot, &mut Rng::new(3));
            chain.insert(slot, slot - 1, true);
        }
        let packed = pack(&chain, &sizes);
        assert_eq!(packed.iter().map(|r| r.3).max().unwrap(), 3);
        assert_eq!(packed.iter().map(|r| r.2).max().unwrap(), 24);
        assert_eq!(tall, 18);
    }
}
