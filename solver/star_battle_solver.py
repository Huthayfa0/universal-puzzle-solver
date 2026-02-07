from .solver import BaseSolver
from copy import copy, deepcopy
import random


class StarBattleSolver(BaseSolver):
    """Solver for Star Battle puzzles.
    
    Star Battle requires placing stars such that:
    - Each row, column, and box has exactly N stars
    - Stars cannot be adjacent (including diagonally)
    """
    
    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        """Initialize the Star Battle solver.
        
        Args:
            info: Dictionary containing:
                - boxes: List of box cell coordinates
                - boxes_table: Box ID for each cell
                - items_per_box: Number of stars per box/row/column
            show_progress: If True, show progress updates during solving.
            partial_solution_callback: Optional callback to display partial solution.
            progress_interval: Interval in seconds for progress updates (default: 10.0).
            partial_interval: Interval in seconds for partial solution display (default: 100.0).
        """
        super().__init__(info, show_progress=show_progress, partial_solution_callback=partial_solution_callback,
                        progress_interval=progress_interval, partial_interval=partial_interval)
        self.boxes = info["boxes"]
        self.boxes_table = self.info["boxes_table"]
        self.stars = self.info["items_per_box"]
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.filling_boxes_cache = {}  # Cache for box filling results
    def encode(self):
        """Encode the board state as a tuple for caching.
        
        Returns:
            Tuple representing the board state.
        """
        encoded = []
        for row in self.board:
            x = 1
            s = 0
            for cell in row:
                s += cell * x
                x *= 3
            encoded.append(s)
        return tuple(encoded)

    def count_row(self, i):
        """Count stars in a row (value 2 represents a star)."""
        return sum(self.board[i][j] == 2 for j in range(self.width))

    def count_col(self, j):
        """Count stars in a column."""
        return sum(self.board[i][j] == 2 for i in range(self.height))

    def count_box(self, v):
        """Count stars in a box."""
        return sum(self.board[i][j] == 2 for i, j in self.boxes[v])

    def has_adjacent_star(self, i, j):
        """Check if there's a star adjacent to the given cell (including diagonals)."""
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                ni, nj = i + di, j + dj
                if 0 <= ni < self.height and 0 <= nj < self.width:
                    if self.board[ni][nj] == 2:
                        return True
        return False
    
    def print_board(self):
        """Print the board with box boundaries (for debugging)."""
        for i in range(self.height):
            for j in range(self.width):
                separator = "|" if (j != self.width - 1 and 
                                   self.boxes_table[i][j] != self.boxes_table[i][j + 1]) else " "
                print(self.board[i][j], end=separator)
            print()
            if i == self.height - 1:
                continue
            for j in range(self.width):
                separator = " " if self.boxes_table[i][j] == self.boxes_table[i + 1][j] else "-"
                print(separator, end=" ")
            print()

    def max_non_adjacent_1d(self, positions):
        # positions: sorted list of indices
        if not positions:
            return 0

        count = 1
        last = positions[0]

        for p in positions[1:]:
            if p > last + 1:
                count += 1
                last = p

        return count

    def can_fit(self,cells, stars):
        """
        Return True iff it's possible to choose >= `stars` cells from `cells`
        such that no two are 8-neighbors. `cells` is an iterable of (r,c).
        Optimized for many repeated calls and small graphs (<= ~50 nodes).
        """
        # normalize & trivial checks
        cells = list(dict.fromkeys(cells))
        n = len(cells)
        if stars <= 0:
            return True
        if n < stars:
            return False
        if stars == 1:
            return True  # at least one node exists

        # index and 8-neighbor adjacency bitmasks
        idx = {c: i for i, c in enumerate(cells)}
        adj = [0] * n
        for i, (r, c) in enumerate(cells):
            m = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    j = idx.get((r + dr, c + dc))
                    if j is not None:
                        m |= 1 << j
            adj[i] = m
        full = (1 << n) - 1

        # ---------- cheap lower bound (greedy). If LB >= stars -> True ----------
        def greedy_lb():
            alive = full
            chosen = 0
            # choose min-degree vertices repeatedly
            while alive:
                best_v = None
                best_deg = 10**9
                mm = alive
                while mm:
                    v = (mm & -mm).bit_length() - 1
                    mm &= mm - 1
                    deg = (adj[v] & alive).bit_count()
                    if deg < best_deg:
                        best_deg = deg
                        best_v = v
                        if best_deg == 0:
                            break
                chosen += 1
                if chosen >= stars:
                    return chosen
                alive &= ~(1 << best_v)
                alive &= ~adj[best_v]
            return chosen

        if greedy_lb() >= stars:
            return True

        # ---------- cheap upper bound: 2x2 tiling (min over 4 shifts). If UB < stars -> False ----------
        def ub_2x2():
            best = n
            for sx in (0, 1):
                for sy in (0, 1):
                    used = set()
                    for (r, c) in cells:
                        used.add(((r - sx) // 2, (c - sy) // 2))
                    if len(used) < best:
                        best = len(used)
            return best

        if ub_2x2() < stars:
            return False

        # ---------- cheap upper bound: greedy matching -> UB = n - matching_size ----------
        def greedy_matching():
            used = 0
            pairs = 0
            order = sorted(range(n), key=lambda v: -(adj[v].bit_count()))
            for v in order:
                if used & (1 << v):
                    continue
                mm = adj[v] & ~used
                if mm:
                    u = (mm & -mm).bit_length() - 1
                    used |= (1 << v) | (1 << u)
                    pairs += 1
            return pairs

        if n - greedy_matching() < stars:
            return False

        # ---------- split into connected components (on original graph) ----------
        seen = 0
        comps = []
        for i in range(n):
            if seen & (1 << i):
                continue
            stack = [i]
            comp_mask = 0
            seen |= (1 << i)
            comp_mask |= (1 << i)
            while stack:
                u = stack.pop()
                nbrs = adj[u] | (1 << u)
                mm = nbrs
                while mm:
                    v = (mm & -mm).bit_length() - 1
                    mm &= mm - 1
                    if not (seen & (1 << v)):
                        seen |= (1 << v)
                        stack.append(v)
                        comp_mask |= (1 << v)
            comps.append(comp_mask)

        # ---------- solve components one by one, early exit when achieved stars ----------
        total = 0
        for comp in comps:
            # if remaining required already satisfied
            need = stars - total
            if need <= 0:
                return True

            # if comp can't provide enough even in best case -> continue
            comp_size = comp.bit_count()
            if comp_size <= 0:
                continue
            if comp_size < need:
                total += comp_size  # best case: all nodes (very loose), but skip deeper work
                if total >= stars:
                    return True
                continue

            # map local indices for component
            verts = []
            pos = {}
            mm = comp
            while mm:
                v = (mm & -mm).bit_length() - 1
                mm &= mm - 1
                pos[v] = len(verts)
                verts.append(v)
            m = len(verts)

            # local adjacency
            local_adj = [0] * m
            for i, orig in enumerate(verts):
                nb = adj[orig] & comp
                mm2 = nb
                mask = 0
                while mm2:
                    v = (mm2 & -mm2).bit_length() - 1
                    mm2 &= mm2 - 1
                    mask |= 1 << pos[v]
                local_adj[i] = mask

            # remove isolated local vertices immediately (they always can be taken)
            iso_count = 0
            base_mask = (1 << m) - 1
            for i in range(m):
                if local_adj[i] == 0:
                    iso_count += 1
                    base_mask &= ~(1 << i)
            if iso_count >= need:
                return True
            need -= iso_count
            if need <= 0:
                return True
            if base_mask == 0:
                total += iso_count
                if total >= stars:
                    return True
                continue

            # exact check on remaining local mask: does the component provide >= need?
            from functools import lru_cache
            @lru_cache(maxsize=None)
            def dfs(mask):
                # returns maximum independent set size for 'mask' (local indices)
                if mask == 0:
                    return 0
                # quick upper bound: popcount(mask) (trivial)
                if mask.bit_count() < 1:
                    return 0
                # pick branching vertex: one with largest degree in mask
                mm = mask
                best_v = None
                best_deg = -1
                while mm:
                    v = (mm & -mm).bit_length() - 1
                    mm &= mm - 1
                    deg = (local_adj[v] & mask).bit_count()
                    if deg > best_deg:
                        best_deg = deg
                        best_v = v
                # take best_v
                take_mask = mask & ~((1 << best_v) | local_adj[best_v])
                take_res = 1 + dfs(take_mask)
                # early pruning: if already large enough compared to need, can stop higher-level caller
                if take_res >= need:
                    return take_res
                # skip best_v
                skip_res = dfs(mask & ~(1 << best_v))
                return take_res if take_res > skip_res else skip_res

            comp_best = dfs(base_mask) + iso_count
            total += comp_best
            if total >= stars:
                return True
            # small optimization: if even taking entire component doesn't reach needed, continue

        return total >= stars


    
    def box_feasible(self, v):
        stars = self.count_box(v)
        if stars > self.stars:
            return False

        candidates = [
            (i, j) for (i, j) in self.boxes[v]
            if self.board[i][j] == 0 and self.can_place_star(i, j)
        ]

        return self.can_fit(candidates,self.stars-stars)
    
    def fill_all_boxes(self):
        key=self.encode()
        updates=key not in self.filling_boxes_cache
        while updates:
            updates = False
            for i in range(self.height):
                for j in range(self.width):
                    if self.board[i][j]!=0:
                        continue
                    if not self.can_place_star(i,j) or not self.test_place_star(i,j):
                        if self.cant_place_empty(i,j) or not self.test_place_empty(i,j):
                            self.filling_boxes_cache[key]=False
                            return False
                        updates= True
                        self.board[i][j]=1
                    elif self.cant_place_empty(i,j) or not self.test_place_empty(i,j):
                        updates= True
                        self.board[i][j]=2
        if key in self.filling_boxes_cache:
            if not self.filling_boxes_cache[key]:
                return False
            self.board= deepcopy(self.filling_boxes_cache[key])
        else:
            self.filling_boxes_cache[key] =deepcopy(self.board)
        return True

    def all_boxes_feasible(self):
        for v in range(len(self.boxes)):
            if not self.box_feasible(v):
                return False
        #check the columns
        for i in range(self.width-1):
            candidates = []
            stars = 0
            for j in range(self.height):
                if self.board[j][i]==2:
                    stars+=1
                elif self.board[j][i]==0 and self.can_place_star(j, i):
                    candidates.append((j,i))
                if self.board[j][i+1]==2:
                    stars+=1
                elif self.board[j][i+1]==0 and self.can_place_star(j,i+1):
                    candidates.append((j,i+1))
            if stars > self.stars * 2:
                return False
            if not self.can_fit(candidates,self.stars*2-stars):
                return False
        for i in range(self.height-1):
            candidates = []
            stars = 0
            for j in range(self.width):
                if self.board[i][j]==2:
                    stars+=1
                elif self.board[i][j]==0 and self.can_place_star(i,j):
                    candidates.append((i,j))
            for j in range(self.width):
                if self.board[i+1][j]==2:
                    stars+=1
                elif self.board[i+1][j]==0 and self.can_place_star(i+1,j):
                    candidates.append((i+1,j))
            if stars > self.stars * 2:
                return False
            if not self.can_fit(candidates,self.stars*2-stars):
                return False   
        return True
    
    def test_place_star(self, i, j):
        board_copy=deepcopy(self.board)
        self.board[i][j] = 2
        v=self.all_boxes_feasible()
        self.board=board_copy
        return v

    def test_place_empty(self, i, j):
        board_copy=deepcopy(self.board)
        self.board[i][j] = 1
        v=self.all_boxes_feasible()
        self.board=board_copy
        return v

    def can_place_star(self, i, j):
        if self.board[i][j] == 2:
            return False
        if self.has_adjacent_star(i, j):
            return False
        if self.count_row(i) >= self.stars:
            return False
        if self.count_col(j) >= self.stars:
            return False
        if self.count_box(self.boxes_table[i][j]) >= self.stars:
            return False
        return True

    def cant_place_empty(self, i, j):
        # ---- Row ----
        stars = self.count_row(i)
        candidates = [
            jj for jj in range(self.width)
            if jj != j and self.board[i][jj] == 0 and self.can_place_star(i, jj)
        ]
        if stars + self.max_non_adjacent_1d(sorted(candidates)) < self.stars:
            return True

        # ---- Column ----
        stars = self.count_col(j)
        candidates = [
            ii for ii in range(self.height)
            if ii != i and self.board[ii][j] == 0 and self.can_place_star(ii, j)
        ]
        if stars + self.max_non_adjacent_1d(sorted(candidates)) < self.stars:
            return True

        # ---- Box ----
        box = self.boxes_table[i][j]
        stars = self.count_box(box)
        candidates = [
            (ii, jj) for ii, jj in self.boxes[box]
            if (ii, jj) != (i, j) and self.board[ii][jj] == 0 and self.can_place_star(ii, jj)
        ]
        if not self.can_fit(candidates,self.stars-stars):
            return True

        return False

    # ---------------------------
    # Backtracking solver
    # ---------------------------

    def solve_puzzle(self, cell_idx=0):
        if cell_idx == self.height * self.width:
            return self.is_complete()
        i, j = self.cells_order[cell_idx]
        if self.board[i][j]!=0:
            return self.solve_puzzle(cell_idx + 1)
        if not self.all_boxes_feasible():
            return False
        if not self.fill_all_boxes():
            return False
        if self.board[i][j]!=0:
            return self.solve_puzzle(cell_idx + 1)
        self.cells_order[cell_idx:] = sorted(self.cells_order[cell_idx:],key=lambda x:sum(self.board[v[0]][v[1]]==0 for v in self.boxes[self.boxes_table[x[0]][x[1]]]))
        
        # Try placing a star
        board_save = deepcopy(self.board)
        if self.can_place_star(i, j):
            self.board[i][j] = 2
            # Mark adjacent cells as empty (cannot have stars)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < self.height and 0 <= nj < self.width:
                        self.board[ni][nj] = 1
            if self.solve_puzzle(cell_idx + 1):
                return True
            self.board = board_save

        # If we can't place a star, must place empty
        if self.cant_place_empty(i, j):
            return False
        self.board[i][j] = 1
        return self.solve_puzzle(cell_idx + 1)

    # ---------------------------
    # Final validation
    # ---------------------------

    def is_complete(self):
        for i in range(self.height):
            if self.count_row(i) != self.stars:
                return False
        for j in range(self.width):
            if self.count_col(j) != self.stars:
                return False
        for v in range(len(self.boxes)):
            if self.count_box(v) != self.stars:
                return False
        return True

    # ---------------------------
    # Entry point
    # ---------------------------

    def solve(self):
        """Solve the Star Battle puzzle.
        
        Returns:
            2D list representing the solved puzzle board, or None if unsolvable.
        """
        self._start_progress_tracking()
        
        self.cells_order = [(i, j) for i in range(self.height) for j in range(self.width)]
        self.cells_order = sorted(
            self.cells_order,
            key=lambda x: sum(self.board[v[0]][v[1]] == 0 for v in self.boxes[self.boxes_table[x[0]][x[1]]])
        )
        
        total_cells = len(self.cells_order)
        backtrack_count = [0]
        call_count = [0]  # Track number of recursive calls for periodic updates
        
        # Initial progress update
        cells_filled = sum(1 for row in self.board for cell in row if cell != 0)
        self._update_progress(
            cell_idx=0,
            total_cells=total_cells,
            cells_filled=cells_filled,
            current_cell=self.cells_order[0] if self.cells_order else None,
            backtrack_count=0,
            call_count=0
        )
        
        def solve_puzzle_with_progress(cell_idx=0):
            """Wrapper to add progress tracking to solve_puzzle."""
            if cell_idx == self.height * self.width:
                return self.is_complete()
            
            i, j = self.cells_order[cell_idx]
            
            # Update progress on every call (timer will print every 10 seconds)
            call_count[0] += 1
            cells_filled = sum(1 for row in self.board for cell in row if cell != 0)
            self._update_progress(
                cell_idx=cell_idx,
                total_cells=total_cells,
                cells_filled=cells_filled,
                current_cell=(i, j),
                backtrack_count=backtrack_count[0],
                call_count=call_count[0]
            )
            
            if self.board[i][j] != 0:
                return solve_puzzle_with_progress(cell_idx + 1)
            
            if not self.all_boxes_feasible():
                backtrack_count[0] += 1
                cells_filled = sum(1 for row in self.board for cell in row if cell != 0)
                self._update_progress(
                    cell_idx=cell_idx,
                    total_cells=total_cells,
                    cells_filled=cells_filled,
                    current_cell=(i, j),
                    backtrack_count=backtrack_count[0],
                    call_count=call_count[0]
                )
                return False
            
            if not self.fill_all_boxes():
                backtrack_count[0] += 1
                cells_filled = sum(1 for row in self.board for cell in row if cell != 0)
                self._update_progress(
                    cell_idx=cell_idx,
                    total_cells=total_cells,
                    cells_filled=cells_filled,
                    current_cell=(i, j),
                    backtrack_count=backtrack_count[0],
                    call_count=call_count[0]
                )
                return False
            
            if self.board[i][j] != 0:
                return solve_puzzle_with_progress(cell_idx + 1)
            self.cells_order[cell_idx:] = sorted(
                self.cells_order[cell_idx:],
                key=lambda x: sum(self.board[v[0]][v[1]] == 0 for v in self.boxes[self.boxes_table[x[0]][x[1]]])
            )
            
            # Try placing a star
            board_save = deepcopy(self.board)
            if self.can_place_star(i, j):
                self.board[i][j] = 2
                # Mark adjacent cells as empty (cannot have stars)
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < self.height and 0 <= nj < self.width:
                            self.board[ni][nj] = 1
                
                # Update progress after placing star
                cells_filled = sum(1 for row in self.board for cell in row if cell != 0)
                self._update_progress(
                    cell_idx=cell_idx,
                    total_cells=total_cells,
                    cells_filled=cells_filled,
                    current_cell=(i, j),
                    backtrack_count=backtrack_count[0],
                    call_count=call_count[0]
                )
                
                if solve_puzzle_with_progress(cell_idx + 1):
                    return True
                self.board = board_save
                backtrack_count[0] += 1
                # Update progress after backtrack
                cells_filled = sum(1 for row in self.board for cell in row if cell != 0)
                self._update_progress(
                    cell_idx=cell_idx,
                    total_cells=total_cells,
                    cells_filled=cells_filled,
                    current_cell=(i, j),
                    backtrack_count=backtrack_count[0],
                    call_count=call_count[0]
                )

            # If we can't place a star, must place empty
            if self.cant_place_empty(i, j):
                return False
            
            self.board[i][j] = 1
            # Update progress after placing empty
            cells_filled = sum(1 for row in self.board for cell in row if cell != 0)
            self._update_progress(
                cell_idx=cell_idx,
                total_cells=total_cells,
                cells_filled=cells_filled,
                current_cell=(i, j),
                backtrack_count=backtrack_count[0],
                call_count=call_count[0]
            )
            return solve_puzzle_with_progress(cell_idx + 1)
        
        try:
            result = solve_puzzle_with_progress()
        finally:
            self._stop_progress_tracking()
        
        if result:
            return self.board
        return None