"""Stitches puzzle solver.

Rules:
- Each neighboring box-pair border must have exactly K stitches.
- A stitch connects 2 orthogonally adjacent cells from different boxes.
- Two stitches cannot share a hole (each cell can be used by at most one stitch).
- Outside clues give hole counts per row/column.
"""

from itertools import combinations

from .solver import BaseSolver


def _clue_val(value):
    """Extract numeric clue from border value (int or list)."""
    if isinstance(value, int):
        return value
    if isinstance(value, list) and value:
        ints = [v for v in value if isinstance(v, int)]
        return sum(ints) if ints else 0
    return 0


class StitchesSolver(BaseSolver):
    """Solver for Stitches puzzles.

    Input uses CombinedTaskParser(BorderTaskParser, BoxesTaskParser):
    - Border part: row/column hole clues (horizontal_borders, vertical_borders).
    - Boxes part: regions and border adjacencies (boxes, boxes_table, boxes_borders).

    Output format for submission:
    - [((r1, c1), (r2, c2)), ...]
      Click (r1, c1) then (r2, c2) for each stitch.
    """

    def __init__(
        self,
        info,
        show_progress=True,
        partial_solution_callback=None,
        progress_interval=10.0,
        partial_interval=100.0,
    ):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.height = info.get("height_2", info["height"])
        self.width = info.get("width_2", info["width"])
        self.boxes = info["boxes"]
        self.boxes_table = info["boxes_table"]
        self.boxes_borders = info["boxes_borders"]
        self.num_boxes = len(self.boxes)

        row_borders = info.get("horizontal_borders") or []
        col_borders = info.get("vertical_borders") or []

        self.row_clues = [_clue_val(row_borders[i]) if i < len(row_borders) else 0 for i in range(self.height)]
        self.col_clues = [_clue_val(col_borders[j]) if j < len(col_borders) else 0 for j in range(self.width)]
        self.stitches_per_pair = sum(self.col_clues) //( sum(len(v) for v in info["boxes_borders"]))

        self.pair_data = []
        self.block_pairs = []
        self.stitches = set()
        self._build_pairs()

    def _build_pairs(self):
        """Build neighboring box pairs and valid K-edge combinations per pair."""
        pair_set = set()
        for b1 in range(self.num_boxes):
            for b2 in self.boxes_borders[b1]:
                pair_set.add((min(b1, b2), max(b1, b2)))
        self.block_pairs = sorted(pair_set)

        for (b1, b2) in self.block_pairs:
            edge_set = set()
            for i, j, direction in self.boxes_borders[b1].get(b2, []):
                ni, nj = i + direction[0], j + direction[1]
                a, b = (i, j), (ni, nj)
                if a > b:
                    a, b = b, a
                edge_set.add((a, b))
            edges = sorted(edge_set)
            if len(edges) < self.stitches_per_pair:
                self.pair_data = []
                return

            combos = []
            for combo in combinations(edges, self.stitches_per_pair):
                used_cells = set()
                ok = True
                for a, b in combo:
                    if a in used_cells or b in used_cells:
                        ok = False
                        break
                    used_cells.add(a)
                    used_cells.add(b)
                if ok:
                    combos.append(combo)
            if not combos:
                self.pair_data = []
                return

            # Keep difficult borders first to reduce branching.
            self.pair_data.append(
                {
                    "pair": (b1, b2),
                    "edges": edges,
                    "combos": combos,
                    "cells": {cell for edge in edges for cell in edge},
                }
            )

        self.pair_data.sort(key=lambda d: (len(d["combos"]), len(d["edges"])))

    def _remaining_capacity_ok(self, next_index, used, row_used, col_used):
        """Prune using row/col upper bounds from cells in remaining borders."""
        rem_row_cap = [0] * self.height
        rem_col_cap = [0] * self.width

        for idx in range(next_index, len(self.pair_data)):
            for r, c in self.pair_data[idx]["cells"]:
                if (r, c) not in used:
                    rem_row_cap[r] += 1
                    rem_col_cap[c] += 1

        for r in range(self.height):
            if row_used[r] > self.row_clues[r]:
                return False
            if row_used[r] + rem_row_cap[r] < self.row_clues[r]:
                return False
        for c in range(self.width):
            if col_used[c] > self.col_clues[c]:
                return False
            if col_used[c] + rem_col_cap[c] < self.col_clues[c]:
                return False
        return True

    def _pair_has_feasible_choice(self, pair_info, used):
        """Check that at least one K-edge choice remains for this border."""
        for combo in pair_info["combos"]:
            if all((a not in used and b not in used) for a, b in combo):
                return True
        return False

    def _search(self, index, used, row_used, col_used, chosen_stitches, call_count, backtrack_count):
        call_count[0] += 1
        if self.progress_tracker and call_count[0] % 500 == 0:
            self._update_progress(
                call_count=call_count[0],
                backtrack_count=backtrack_count[0],
                pairs_done=index,
                total_pairs=len(self.pair_data),
            )

        if index == len(self.pair_data):
            return row_used == self.row_clues and col_used == self.col_clues

        if not self._remaining_capacity_ok(index, used, row_used, col_used):
            return False

        # Forward-check: every remaining border must still be satisfiable.
        for j in range(index, len(self.pair_data)):
            if not self._pair_has_feasible_choice(self.pair_data[j], used):
                return False

        pair_info = self.pair_data[index]
        for combo in pair_info["combos"]:
            combo_cells = []
            row_add = [0] * self.height
            col_add = [0] * self.width
            valid = True

            for a, b in combo:
                if a in used or b in used:
                    valid = False
                    break
                combo_cells.append(a)
                combo_cells.append(b)
                row_add[a[0]] += 1
                row_add[b[0]] += 1
                col_add[a[1]] += 1
                col_add[b[1]] += 1

            if not valid:
                continue

            if any(row_used[r] + row_add[r] > self.row_clues[r] for r in range(self.height)):
                continue
            if any(col_used[c] + col_add[c] > self.col_clues[c] for c in range(self.width)):
                continue

            for r, c in combo_cells:
                used.add((r, c))
            for r in range(self.height):
                row_used[r] += row_add[r]
            for c in range(self.width):
                col_used[c] += col_add[c]
            for edge in combo:
                chosen_stitches.append(edge)

            if self._search(index + 1, used, row_used, col_used, chosen_stitches, call_count, backtrack_count):
                return True

            for _ in combo:
                chosen_stitches.pop()
            for r in range(self.height):
                row_used[r] -= row_add[r]
            for c in range(self.width):
                col_used[c] -= col_add[c]
            for r, c in combo_cells:
                used.remove((r, c))
            backtrack_count[0] += 1

        return False

    def solve(self):
        """Solve puzzle and return stitches as [((r1,c1), (r2,c2)), ...]."""
        if not self.pair_data and self.block_pairs:
            return None

        total_holes = sum(self.row_clues)
        if total_holes != sum(self.col_clues):
            return None
        required_holes = 2 * len(self.block_pairs) * self.stitches_per_pair
        if total_holes != required_holes:
            return None

        used = set()
        row_used = [0] * self.height
        col_used = [0] * self.width
        chosen_stitches = []
        call_count = [0]
        backtrack_count = [0]

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = self._search(0, used, row_used, col_used, chosen_stitches, call_count, backtrack_count)
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None

        self.stitches = set(chosen_stitches)
        self.info["stitches"] = self.stitches
        return [((a[0], a[1]), (b[0], b[1])) for (a, b) in sorted(self.stitches)]
