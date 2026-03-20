"""Light Up puzzle solver.

Rules:
- Place light bulbs on white cells so every white cell is illuminated.
- A cell is illuminated by a bulb if they share a row or column with no wall between them.
- No two bulbs may see each other (same row/column, no wall between).
- Numbered walls: exactly that many bulbs must be directly adjacent (touching).
"""

from .solver import BaseSolver

WHITE = -2
WALL = -1

_D4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def _normalize_grid(table, height, width):
    """Convert parsed table to solver grid.

    Parser encoding -> internal:
      0      -> WHITE (fillable)
      "B"    -> WALL  (no clue)
      "Zero" -> 0     (wall with clue 0)
      1..4   -> 1..4  (wall with clue)
    """
    grid = [[WHITE] * width for _ in range(height)]
    for r in range(height):
        for c in range(width):
            v = table[r][c]
            if v == 0:
                grid[r][c] = WHITE
            elif v == "B":
                grid[r][c] = WALL
            elif v == "Zero":
                grid[r][c] = 0
            elif isinstance(v, int) and 1 <= v <= 4:
                grid[r][c] = v
    return grid


class LightUpSolver(BaseSolver):
    """Solver for Light Up puzzles."""

    def __init__(self, info, show_progress=True, partial_solution_callback=None,
                 progress_interval=10.0, partial_interval=100.0):
        super().__init__(info, show_progress=show_progress,
                         partial_solution_callback=partial_solution_callback,
                         progress_interval=progress_interval,
                         partial_interval=partial_interval)

        self.grid = _normalize_grid(info["table"], self.height, self.width)
        self.board = [[0] * self.width for _ in range(self.height)]
        self.assigned = [[False] * self.width for _ in range(self.height)]

        self.white_cells = []
        self.numbered_walls = []
        for r in range(self.height):
            for c in range(self.width):
                if self.grid[r][c] == WHITE:
                    self.white_cells.append((r, c))
                elif isinstance(self.grid[r][c], int) and 0 <= self.grid[r][c] <= 4:
                    self.numbered_walls.append((r, c))

        # Precompute per white cell: visible white cells along rays (row/col until wall)
        self._visible = {}
        for r, c in self.white_cells:
            vis = []
            for dr, dc in _D4:
                nr, nc = r + dr, c + dc
                while 0 <= nr < self.height and 0 <= nc < self.width and self.grid[nr][nc] == WHITE:
                    vis.append((nr, nc))
                    nr += dr
                    nc += dc
            self._visible[(r, c)] = vis

        # Precompute per white cell: adjacent numbered walls
        self._adj_walls = {}
        for r, c in self.white_cells:
            walls = []
            for dr, dc in _D4:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.height and 0 <= nc < self.width:
                    g = self.grid[nr][nc]
                    if isinstance(g, int) and 0 <= g <= 4:
                        walls.append((nr, nc))
            self._adj_walls[(r, c)] = walls

        # Initial order only for deterministic iteration; actual branch order is dynamic (MRV).
        self.white_cells.sort(key=lambda rc: (
            0 if self._adj_walls[rc] else 1,
            len(self._visible[rc]),
            rc[0],
            rc[1],
        ))

    def _wall_flex_and_deficit(self, wr, wc):
        """Flex slots (can still be bulb) and bulbs still needed for this clue."""
        clue = self.grid[wr][wc]
        bulbs = self._bulbs_touching_wall(wr, wc)
        deficit = clue - bulbs
        flex = 0
        for dr, dc in _D4:
            nr, nc = wr + dr, wc + dc
            if 0 <= nr < self.height and 0 <= nc < self.width and self.grid[nr][nc] == WHITE:
                if self.board[nr][nc] != 1 and self._can_place_bulb_here(nr, nc):
                    flex += 1
        return flex, deficit

    def _dead_dirs_without_placeable_bulb(self, r, c):
        """Cardinal directions from (r,c) where no white on the ray can still host a bulb."""
        dead_dirs = 0
        for dr, dc in _D4:
            placeable_on_ray = False
            nr, nc = r + dr, c + dc
            while 0 <= nr < self.height and 0 <= nc < self.width and self.grid[nr][nc] == WHITE:
                if self._can_place_bulb_here(nr, nc):
                    placeable_on_ray = True
                    break
                nr += dr
                nc += dc
            if not placeable_on_ray:
                dead_dirs += 1
        return dead_dirs

    def _mrv_key(self, r, c):
        """Lower tuple = branch this white cell first (minimum remaining values + clue tightness).

        - Prefer 1 branch over 2 (forced by LOS / count walls).
        - Prefer cells touching a wall with little slack (flex - deficit).
        - Prefer cells with more cardinal directions where no bulb can ever be placed on the ray
          (harder to become lit from afar → fail fast unless this cell is the lamp).
        """
        may_bulb = (
            not self._sees_bulb(r, c) and self._adjacent_clues_allow_new_bulb(r, c)
        )
        choices = 2 if may_bulb else 1

        min_slack = 10**9
        wall_count = len(self._adj_walls[(r, c)])
        for wr, wc in self._adj_walls[(r, c)]:
            flex, deficit = self._wall_flex_and_deficit(wr, wc)
            slack = flex - deficit
            if slack < min_slack:
                min_slack = slack
        if wall_count == 0:
            min_slack = 10**9

        dead_dirs = self._dead_dirs_without_placeable_bulb(r, c)

        return (
            choices,
            min_slack,
            -dead_dirs,
            -wall_count,
            len(self._visible[(r, c)]),
            r,
            c,
        )

    def _pick_next_white(self):
        """Unassigned white with best (lowest) MRV key, or None if all assigned."""
        best = None
        best_key = None
        for r, c in self.white_cells:
            if self.assigned[r][c]:
                continue
            k = self._mrv_key(r, c)
            if best_key is None or k < best_key:
                best_key = k
                best = (r, c)
        return best

    # -- constraint checks ----------------------------------------------------

    def _sees_bulb(self, r, c):
        """True if a bulb at (r,c) would see another existing bulb."""
        for nr, nc in self._visible[(r, c)]:
            if self.board[nr][nc] == 1:
                return True
        return False

    def _is_lit(self, r, c):
        """True if (r,c) is illuminated by any placed bulb."""
        if self.board[r][c] == 1:
            return True
        for nr, nc in self._visible[(r, c)]:
            if self.board[nr][nc] == 1:
                return True
        return False

    def _bulbs_touching_wall(self, wr, wc):
        """Count bulbs on white cells adjacent to numbered wall (wr, wc)."""
        n = 0
        for dr, dc in _D4:
            ar, ac = wr + dr, wc + dc
            if 0 <= ar < self.height and 0 <= ac < self.width and self.board[ar][ac] == 1:
                n += 1
        return n

    def _adjacent_clues_allow_new_bulb(self, r, c):
        """True if placing a bulb at (r,c) would not exceed any adjacent clue."""
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                g = self.grid[nr][nc]
                if isinstance(g, int) and 0 <= g <= 4:
                    if self._bulbs_touching_wall(nr, nc) >= g:
                        return False
        return True

    def _can_place_bulb_here(self, r, c):
        """True if (r,c) is white and could still be a bulb in some completion."""
        if self.grid[r][c] != WHITE:
            return False
        if self.board[r][c] == 1:
            return True
        if self.assigned[r][c]:
            return False  # committed empty
        if self._sees_bulb(r, c):
            return False
        return self._adjacent_clues_allow_new_bulb(r, c)

    def _can_still_be_lit(self, r, c):
        """True if (r,c) is already lit, or a bulb could still appear ahead on some ray.

        Light passes through empty white cells; an unassigned cell that cannot host a bulb
        is treated as future-empty for that ray.
        """
        if self.board[r][c] == 1:
            return True
        # This cell may still become a bulb (including isolated whites with no white neighbors).
        if not self.assigned[r][c] and self._can_place_bulb_here(r, c):
            return True
        for dr, dc in _D4:
            nr, nc = r + dr, c + dc
            while 0 <= nr < self.height and 0 <= nc < self.width and self.grid[nr][nc] == WHITE:
                if self.board[nr][nc] == 1:
                    return True
                if not self.assigned[nr][nc]:
                    if self._can_place_bulb_here(nr, nc):
                        return True
                    # blocked for bulbs (sees bulb or clue full); light may still pass through
                # assigned, no bulb: empty cell, light continues
                nr += dr
                nc += dc
        return False

    def _wall_ok(self, wr, wc):
        """Numbered wall: clue not exceeded, and enough *unblocked* adjacent slots remain.

        An adjacent white cell blocked by existing bulbs (cannot host a bulb) does not
        count toward remaining capacity — otherwise we miss dead-ends when lights
        block filling counted walls.
        """
        clue = self.grid[wr][wc]
        bulbs = 0
        can_place = 0
        for dr, dc in _D4:
            nr, nc = wr + dr, wc + dc
            if 0 <= nr < self.height and 0 <= nc < self.width and self.grid[nr][nc] == WHITE:
                if self.board[nr][nc] == 1:
                    bulbs += 1
                elif self._can_place_bulb_here(nr, nc):
                    can_place += 1
                # else: committed empty or unassigned-but-blocked — cannot add a bulb here
        return bulbs <= clue and bulbs + can_place >= clue

    def _all_numbered_walls_ok(self):
        """Every clue wall must still be satisfiable (used after each assignment)."""
        for wr, wc in self.numbered_walls:
            if not self._wall_ok(wr, wc):
                return False
        return True

    def _revert_patches(self, undo):
        """Restore board/assigned from a list of (r, c, old_board, old_assigned)."""
        for r, c, ob, oa in reversed(undo):
            self.board[r][c] = ob
            self.assigned[r][c] = oa

    def _light_source_candidates(self, r, c):
        """Cells that could become a bulb and illuminate (r,c). Returns list (max 2)."""
        sources = []
        if not self.assigned[r][c] and self._can_place_bulb_here(r, c):
            sources.append((r, c))
        if len(sources) < 2:
            for dr, dc in _D4:
                nr, nc = r + dr, c + dc
                while 0 <= nr < self.height and 0 <= nc < self.width and self.grid[nr][nc] == WHITE:
                    if not self.assigned[nr][nc] and self._can_place_bulb_here(nr, nc):
                        sources.append((nr, nc))
                        if len(sources) >= 2:
                            break
                    nr += dr
                    nc += dc
                if len(sources) >= 2:
                    break
        return sources

    def _force_bulb(self, fr, fc, undo):
        """Place a forced bulb at (fr, fc). Returns False on contradiction."""
        if self.board[fr][fc] == 1:
            return True
        if self._sees_bulb(fr, fc):
            return False
        undo.append((fr, fc, self.board[fr][fc], self.assigned[fr][fc]))
        self.board[fr][fc] = 1
        self.assigned[fr][fc] = True
        return self._check_after_assign(fr, fc)

    def _propagate(self, undo):
        """Run all deduction rules in a fixpoint loop.

        Rules applied each pass:
        1. Numbered-wall clue deductions (force bulbs / empties around satisfied clues).
        2. Forced illumination: if an unlit cell has exactly one possible light source,
           that source must be a bulb.

        Returns False on contradiction.
        """
        while True:
            if not self._all_numbered_walls_ok():
                return False
            changed = False

            # --- Rule 1: numbered wall deductions ---
            for wr, wc in self.numbered_walls:
                clue = self.grid[wr][wc]
                flex = []
                bulbs = 0
                for dr, dc in _D4:
                    nr, nc = wr + dr, wc + dc
                    if 0 <= nr < self.height and 0 <= nc < self.width and self.grid[nr][nc] == WHITE:
                        if self.board[nr][nc] == 1:
                            bulbs += 1
                        elif self._can_place_bulb_here(nr, nc):
                            flex.append((nr, nc))

                if bulbs > clue or bulbs + len(flex) < clue:
                    return False

                if bulbs + len(flex) == clue:
                    for fr, fc in flex:
                        if not self._force_bulb(fr, fc, undo):
                            return False
                        changed = True

                if bulbs == clue:
                    for dr, dc in _D4:
                        nr, nc = wr + dr, wc + dc
                        if not (0 <= nr < self.height and 0 <= nc < self.width and self.grid[nr][nc] == WHITE):
                            continue
                        if self.board[nr][nc] == 1 or self.assigned[nr][nc]:
                            continue
                        undo.append((nr, nc, self.board[nr][nc], self.assigned[nr][nc]))
                        self.assigned[nr][nc] = True
                        self.board[nr][nc] = 0
                        if not self._check_after_assign(nr, nc):
                            return False
                        changed = True

            # --- Rule 2: forced illumination ---
            for r, c in self.white_cells:
                if self._is_lit(r, c):
                    continue
                sources = self._light_source_candidates(r, c)
                if len(sources) == 0:
                    return False
                if len(sources) == 1:
                    if not self._force_bulb(sources[0][0], sources[0][1], undo):
                        return False
                    changed = True

            if not changed:
                break
        return True

    def _check_after_assign(self, r, c):
        """Run all constraint checks after assigning (r,c). Returns False to backtrack."""
        # 1. All clue walls — new bulbs block line-of-sight far from the cell we just set
        if not self._all_numbered_walls_ok():
            return False
        # 2. This cell itself must still be lightable
        if not self._can_still_be_lit(r, c):
            return False
        # 3. Cells on same rows/cols (rays) may have broken lighting
        affected = {(r, c)}
        for nr, nc in self._visible[(r, c)]:
            affected.add((nr, nc))
        for ar, ac in affected:
            if self.assigned[ar][ac] and not self._can_still_be_lit(ar, ac):
                return False
        return True

    # -- solve ----------------------------------------------------------------

    def solve(self):
        """Solve the Light Up puzzle. Returns 2D grid with 0=no bulb, 1=bulb."""
        n = len(self.white_cells)
        call_count = [0]
        backtrack_count = [0]

        def verify_complete():
            """All whites decided, fully lit, and each clue wall has exactly its count."""
            for r, c in self.white_cells:
                if not self.assigned[r][c]:
                    return False
            for r, c in self.white_cells:
                if not self._is_lit(r, c):
                    return False
            for wr, wc in self.numbered_walls:
                bulbs = sum(
                    1 for dr, dc in _D4
                    if (0 <= wr + dr < self.height and 0 <= wc + dc < self.width
                        and self.board[wr + dr][wc + dc] == 1)
                )
                if bulbs != self.grid[wr][wc]:
                    return False
            return True

        def backtrack():
            call_count[0] += 1
            if self.show_progress and self.progress_tracker and call_count[0] % 500 == 0:
                filled = sum(1 for r, c in self.white_cells if self.assigned[r][c])
                self._update_progress(
                    call_count=call_count[0],
                    backtrack_count=backtrack_count[0],
                    cells_filled=filled,
                    total_cells=n,
                )

            propagate_undo = []
            if not self._propagate(propagate_undo):
                self._revert_patches(propagate_undo)
                backtrack_count[0] += 1
                return False

            nxt = self._pick_next_white()
            if nxt is None:
                ok = verify_complete()
                if ok:
                    return True
                self._revert_patches(propagate_undo)
                backtrack_count[0] += 1
                return False

            r, c = nxt
            may_place_bulb = (
                not self._sees_bulb(r, c) and self._adjacent_clues_allow_new_bulb(r, c)
            )
            dd = self._dead_dirs_without_placeable_bulb(r, c)
            self.assigned[r][c] = True

            if not may_place_bulb:
                self.board[r][c] = 0
                if self._check_after_assign(r, c) and backtrack():
                    return True
                backtrack_count[0] += 1
                self.assigned[r][c] = False
                self._revert_patches(propagate_undo)
                return False

            # Value order: many dead directions → try bulb first (often the only local lamp).
            # Otherwise try empty first (fewer bulb–bulb line conflicts on open boards).
            if dd >= 2:
                try_order = (1, 0)
            else:
                try_order = (0, 1)

            for i, val in enumerate(try_order):
                self.board[r][c] = val
                if self._check_after_assign(r, c) and backtrack():
                    return True
                if i == 0:
                    backtrack_count[0] += 1

            backtrack_count[0] += 1
            self.board[r][c] = 0
            self.assigned[r][c] = False
            self._revert_patches(propagate_undo)
            return False

        if self.show_progress and self.progress_tracker:
            self._start_progress_tracking()
        try:
            ok = backtrack()
        finally:
            if self.show_progress and self.progress_tracker:
                self._stop_progress_tracking()

        if not ok:
            return None
        return [row[:] for row in self.board]
