"""Norinori puzzle solver.

Rules:
- Exactly 2 cells are shaded in each region.
- Each shaded cell is part of a 1x2 or 2x1 domino.
- Dominoes may cross region borders.
- Different dominoes may not touch orthogonally.
"""

import sys

from .solver import BaseSolver

_D4 = ((0, 1), (1, 0), (0, -1), (-1, 0))


class NorinoriSolver(BaseSolver):

    def __init__(self, info, show_progress=True, partial_solution_callback=None,
                 progress_interval=10.0, partial_interval=100.0):
        super().__init__(info, show_progress=show_progress,
                         partial_solution_callback=partial_solution_callback,
                         progress_interval=progress_interval,
                         partial_interval=partial_interval)
        self.boxes = info["boxes"]
        self.boxes_table = info["boxes_table"]
        self.num_regions = len(self.boxes)

    def solve(self):
        H, W = self.height, self.width
        N = H * W
        num_regions = self.num_regions
        tracker = self.progress_tracker

        def board_from_mask(mask):
            board = [[0] * W for _ in range(H)]
            for k in range(N):
                if mask & (1 << k):
                    board[k // W][k % W] = 1
            return board

        # Keep a board attribute so BaseSolver progress updates can carry snapshots.
        self.board = board_from_mask(0)
        if tracker:
            self._update_progress(
                call_count=0,
                cells_filled=0,
                total_cells=2 * num_regions,
                current_board=self.board,
            )

        bit = tuple(1 << k for k in range(N))
        cell_reg = tuple(self.boxes_table[i][j] for i in range(H) for j in range(W))
        reg_cells = tuple(tuple(i * W + j for i, j in cells) for cells in self.boxes)
        corner_mask_global = 0
        for i, j in ((0, 0), (0, W - 1), (H - 1, 0), (H - 1, W - 1)):
            corner_mask_global |= 1 << (i * W + j)
        edge_mask_global = 0
        for i in range(H):
            for j in range(W):
                if i == 0 or i == H - 1 or j == 0 or j == W - 1:
                    edge_mask_global |= 1 << (i * W + j)

        for rid in range(num_regions):
            if len(reg_cells[rid]) <= 1:
                return None

        nbr_mask = [0] * N
        nbr_list = [[] for _ in range(N)]
        for i in range(H):
            for j in range(W):
                k = i * W + j
                for di, dj in _D4:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < H and 0 <= nj < W:
                        nk = ni * W + nj
                        nbr_list[k].append(nk)
                        nbr_mask[k] |= bit[nk]

        # Precompute candidate dominoes per region.
        # same[rid]: (a, b, conflict_mask, pair_mask) where both in rid
        # cross[rid]: (a, b, other_rid, conflict_mask, pair_mask)
        same = []
        cross = []
        for rid in range(num_regions):
            s = []
            c = []
            for a in reg_cells[rid]:
                for b in nbr_list[a]:
                    r2 = cell_reg[b]
                    pair_mask = bit[a] | bit[b]
                    # Cells orthogonally adjacent to this domino, excluding its partner cells.
                    conflict_mask = (nbr_mask[a] ^ bit[b]) | (nbr_mask[b] ^ bit[a])
                    if r2 == rid:
                        if b < a:
                            continue
                        s.append((a, b, conflict_mask, pair_mask))
                    else:
                        c.append((a, b, r2, conflict_mask, pair_mask))
            same.append(tuple(s))
            cross.append(tuple(c))

        def find_independent_groups():
            # Regions interact if any cells are within Manhattan distance <= 2.
            adj = [set() for _ in range(num_regions)]
            for rid in range(num_regions):
                for k in reg_cells[rid]:
                    i, j = divmod(k, W)
                    for di in range(-2, 3):
                        for dj in range(-2, 3):
                            if abs(di) + abs(dj) > 2:
                                continue
                            ni, nj = i + di, j + dj
                            if 0 <= ni < H and 0 <= nj < W:
                                r2 = cell_reg[ni * W + nj]
                                if r2 != rid:
                                    adj[rid].add(r2)
            groups = []
            seen = [False] * num_regions
            for rid in range(num_regions):
                if seen[rid]:
                    continue
                comp = []
                stack = [rid]
                while stack:
                    cur = stack.pop()
                    if seen[cur]:
                        continue
                    seen[cur] = True
                    comp.append(cur)
                    for nxt in adj[cur]:
                        if not seen[nxt]:
                            stack.append(nxt)
                groups.append(tuple(comp))
            return groups

        call_count = [0]

        def solve_component(component, start_shaded):
            comp_set = set(component)
            rem = [2 if rid in comp_set else 0 for rid in range(num_regions)]
            eliminated = [0] * num_regions
            comp_cells_mask = 0
            for rid in component:
                for k in reg_cells[rid]:
                    comp_cells_mask |= bit[k]
            reg_mask = [0] * num_regions
            reg_corner_mask = [0] * num_regions
            reg_edge_mask = [0] * num_regions
            for rid in component:
                mask = 0
                for k in reg_cells[rid]:
                    mask |= bit[k]
                reg_mask[rid] = mask
                reg_corner_mask[rid] = mask & corner_mask_global
                reg_edge_mask[rid] = mask & edge_mask_global

            shaded = [start_shaded]
            active = sorted(component)
            same_local = [()] * num_regions
            cross_local = [()] * num_regions
            outside = ~comp_cells_mask
            for rid in active:
                s_keep = []
                c_keep = []
                for a, b, conflict_mask, pair_mask in same[rid]:
                    if pair_mask & outside:
                        continue
                    s_keep.append((a, b, conflict_mask, pair_mask))
                for a, b, r2, conflict_mask, pair_mask in cross[rid]:
                    if pair_mask & outside:
                        continue
                    c_keep.append((a, b, r2, conflict_mask, pair_mask))
                same_local[rid] = tuple(s_keep)
                cross_local[rid] = tuple(c_keep)

            def apply_conflict_elims(a, b, current_s):
                """Eliminate all cells adjacent to placed domino (a,b)."""
                changes = []
                conflict = (nbr_mask[a] | nbr_mask[b]) & ~bit[a] & ~bit[b] & ~current_s
                while conflict:
                    low = conflict & -conflict
                    conflict ^= low
                    c = low.bit_length() - 1
                    r = cell_reg[c]
                    if not (eliminated[r] & low):
                        eliminated[r] |= low
                        changes.append((r, low))
                return changes

            def undo_elims(changes):
                for r, mask in changes:
                    eliminated[r] ^= mask

            def rollback_propagation(s, forced, elim_changes):
                for r2, mask in reversed(elim_changes):
                    eliminated[r2] ^= mask
                for a, b in reversed(forced):
                    s ^= bit[a] | bit[b]
                    unplace_domino(a, b)
                shaded[0] = s

            def place_domino(a, b, current_s, tracked_forced=None, tracked_elims=None):
                current_s |= bit[a] | bit[b]
                rem[cell_reg[a]] -= 1
                rem[cell_reg[b]] -= 1
                if tracked_forced is not None:
                    tracked_forced.append((a, b))
                ce = apply_conflict_elims(a, b, current_s)
                if tracked_elims is not None:
                    tracked_elims.extend(ce)
                return current_s, ce

            def unplace_domino(a, b):
                rem[cell_reg[a]] += 1
                rem[cell_reg[b]] += 1

            def collect_region_options(rid, s):
                r_need = rem[rid]
                if r_need <= 0:
                    return []

                elim_rid = eliminated[rid]
                same_doms = []
                cross_doms = []
                if r_need == 2:
                    for a, b, conflict_mask, pair_mask in same_local[rid]:
                        if pair_mask & elim_rid:
                            continue
                        if (s & pair_mask) or (s & conflict_mask):
                            continue
                        same_doms.append((a, b, conflict_mask, pair_mask))
                for a, b, r2, conflict_mask, pair_mask in cross_local[rid]:
                    if rem[r2] <= 0:
                        continue
                    if pair_mask & (elim_rid | eliminated[r2]):
                        continue
                    if (s & pair_mask) or (s & conflict_mask):
                        continue
                    cross_doms.append((a, b, r2, conflict_mask, pair_mask))

                options = []
                seen = set()
                rid_mask = reg_mask[rid]

                if r_need == 2:
                    for a, b, _, pair_mask in same_doms:
                        doms = ((a, b),)
                        options.append((doms, pair_mask & rid_mask))

                    for idx in range(len(cross_doms)):
                        a1, b1, r21, conflict1, pair1 = cross_doms[idx]
                        for jdx in range(idx + 1, len(cross_doms)):
                            a2, b2, r22, conflict2, pair2 = cross_doms[jdx]
                            if pair1 & pair2:
                                continue
                            if (pair1 & conflict2) or (pair2 & conflict1):
                                continue
                            if r21 == r22 and rem[r21] < 2:
                                continue
                            region_mask = (pair1 | pair2) & rid_mask
                            if region_mask.bit_count() != 2:
                                continue
                            doms = tuple(sorted(((a1, b1), (a2, b2))))
                            if doms in seen:
                                continue
                            seen.add(doms)
                            options.append((doms, region_mask))
                else:
                    for a, b, _, _, pair_mask in cross_doms:
                        doms = ((a, b),)
                        options.append((doms, pair_mask & rid_mask))

                return options

            def propagate_and_select():
                s = shaded[0]
                forced = []
                elim_changes = []
                while True:
                    best_rid = -1
                    best_doms = None
                    best_key = None
                    forced_this_round = False
                    best_force = None
                    best_elim = None
                    min_possible_count = None

                    for rid in active:
                        if rem[rid] <= 0:
                            continue
                        free_mask = reg_mask[rid] & ~s & ~eliminated[rid]
                        free_count = free_mask.bit_count()
                        if free_count < rem[rid]:
                            rollback_propagation(s, forced, elim_changes)
                            return None

                        options = collect_region_options(rid, s)
                        nd = len(options)
                        if nd == 0:
                            rollback_propagation(s, forced, elim_changes)
                            return None

                        possible_mask = 0
                        rmask = reg_mask[rid]
                        for _, region_mask in options:
                            possible_mask |= region_mask & rmask
                        possible_count = possible_mask.bit_count()
                        if possible_count < rem[rid]:
                            rollback_propagation(s, forced, elim_changes)
                            return None

                        if min_possible_count is None or possible_count < min_possible_count:
                            min_possible_count = possible_count

                        # Cells that cannot belong to any valid domino are eliminated.
                        new_elim = free_mask & ~possible_mask
                        if new_elim:
                            key = (
                                possible_count,
                                0 if (free_mask & reg_corner_mask[rid]) else 1,
                                0 if (free_mask & reg_edge_mask[rid]) else 1,
                                nd,
                                len(reg_cells[rid]),
                            )
                            if best_elim is None or key < best_elim[0]:
                                best_elim = (key, rid, new_elim)

                        # If every still-possible cell in this region is mandatory,
                        # any mandatory cell with a unique candidate immediately forces.
                        force_pair = None
                        force_key = None
                        if nd == 1:
                            force_pair = options[0][0]
                            force_key = (
                                possible_count,
                                nd,
                                0 if (free_mask & reg_corner_mask[rid]) else 1,
                                0 if (free_mask & reg_edge_mask[rid]) else 1,
                                len(reg_cells[rid]),
                            )
                        if possible_count == rem[rid]:
                            common_doms = set(options[0][0])
                            for opt_doms, _ in options[1:]:
                                common_doms.intersection_update(opt_doms)
                            if common_doms:
                                force_pair = tuple(sorted(common_doms))
                                force_key = (
                                    possible_count,
                                    nd,
                                    0 if (free_mask & reg_corner_mask[rid]) else 1,
                                    0 if (free_mask & reg_edge_mask[rid]) else 1,
                                    len(reg_cells[rid]),
                                )
                            mm = possible_mask
                            while mm:
                                one = mm & -mm
                                mm ^= one
                                hits = set()
                                for opt_doms, region_mask in options:
                                    if not (region_mask & one):
                                        continue
                                    for dom in opt_doms:
                                        dom_mask = (bit[dom[0]] | bit[dom[1]]) & rmask
                                        if dom_mask & one:
                                            hits.add(dom)
                                        if len(hits) > 1:
                                            break
                                    if len(hits) > 1:
                                        break
                                if len(hits) == 0:
                                    rollback_propagation(s, forced, elim_changes)
                                    return None
                                if len(hits) == 1:
                                    force_pair = tuple(sorted(hits))
                                    force_key = (
                                        possible_count,
                                        nd,
                                        0 if (free_mask & reg_corner_mask[rid]) else 1,
                                        0 if (free_mask & reg_edge_mask[rid]) else 1,
                                        len(reg_cells[rid]),
                                    )
                                    break
                        if force_pair is not None:
                            if best_force is None or force_key < best_force[0]:
                                best_force = (force_key, force_pair)

                        if possible_count != min_possible_count:
                            continue

                        corner_free = (possible_mask & reg_corner_mask[rid]).bit_count()
                        edge_free = (possible_mask & reg_edge_mask[rid]).bit_count()
                        # Order: smallest unresolved region first, then prioritize
                        # corner/edge-frontier regions to extract easy deductions early.
                        key = (
                            possible_count,
                            nd,
                            0 if corner_free > 0 else 1,
                            0 if edge_free > 0 else 1,
                            free_count,
                            len(reg_cells[rid]),
                        )
                        if best_key is None or key < best_key:
                            best_key = key
                            best_rid = rid
                            best_doms = options

                    if best_force is not None:
                        for a, b in best_force[1]:
                            s, _ = place_domino(a, b, s, tracked_forced=forced, tracked_elims=elim_changes)
                        forced_this_round = True
                    elif best_elim is not None:
                        _, rid, new_elim = best_elim
                        eliminated[rid] |= new_elim
                        elim_changes.append((rid, new_elim))
                        forced_this_round = True

                    if not forced_this_round:
                        shaded[0] = s
                        if best_doms is None:
                            return forced, elim_changes, best_rid, []
                        return forced, elim_changes, best_rid, [opt_doms for opt_doms, _ in best_doms]

            dead_states = set()
            def dfs():
                call_count[0] += 1
                if tracker and (call_count[0] & 0x1F) == 0:
                    current_board = board_from_mask(shaded[0])
                    self.board = current_board
                    self._update_progress(
                        call_count=call_count[0],
                        cells_filled=bin(shaded[0]).count("1"),
                        total_cells=2 * num_regions,
                        current_board=current_board,
                    )

                state_key = (
                    shaded[0] & comp_cells_mask,
                    tuple(rem[rid] for rid in active),
                    tuple(eliminated[rid] for rid in active),
                )
                if state_key in dead_states:
                    return False

                step = propagate_and_select()
                if step is None:
                    dead_states.add(state_key)
                    return False

                forced, elim_changes, rid, doms = step
                if rid < 0:
                    return True

                base = shaded[0]
                for option in doms:
                    shaded[0] = base
                    branch_elim = []
                    placed = []
                    for a, b in option:
                        shaded[0], ce = place_domino(a, b, shaded[0])
                        branch_elim.extend(ce)
                        placed.append((a, b))
                    if dfs():
                        return True
                    undo_elims(branch_elim)
                    for a, b in reversed(placed):
                        unplace_domino(a, b)

                shaded[0] = base
                rollback_propagation(shaded[0], forced, elim_changes)
                dead_states.add(state_key)
                return False

            return shaded[0] if dfs() else None

        groups = find_independent_groups()

        if self.show_progress and tracker:
            self._start_progress_tracking()
        try:
            shaded = 0
            # Small components first to prune quickly.
            groups = sorted(groups, key=lambda g: sum(len(reg_cells[r]) for r in g))
            for group in groups:
                solved = solve_component(group, shaded)
                if solved is None:
                    return None
                shaded = solved
        finally:
            if self.show_progress and tracker:
                self._stop_progress_tracking()

        board = [[0] * W for _ in range(H)]
        for k in range(N):
            if shaded & bit[k]:
                board[k // W][k % W] = 1
        self.board = board
        return board
