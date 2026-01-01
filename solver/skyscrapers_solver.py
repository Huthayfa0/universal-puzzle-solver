from .solver import BaseSolver
from itertools import combinations
from math import factorial
class SkyscrapersSolver(BaseSolver):
    def __init__(self, info):
        super().__init__(info)
        self.board = self.info["table"] if "table" in self.info else [[ 0 for _ in range(self.width)] for _ in range(self.height) ]
        self.upper_clues = self.info["vertical_borders"][:self.width]
        self.lower_clues = self.info["vertical_borders"][self.width:]
        self.left_clues  = self.info["horizontal_borders"][:self.height]
        self.right_clues = self.info["horizontal_borders"][self.height:]
        self.scrapers_states=[[] for _ in range(self.width +1)]
        def generate_states(seq = [],scrapers_seen=0, max_val=0):
            if len(seq)==self.width:
                self.scrapers_states[scrapers_seen].append(seq.copy())
                return
            used = set(seq) - {0}
            remaining = sorted(set(range(1, self.width + 1)) - used)
            if max_val >= self.width-1:
                rem_set =set(remaining)
                seq += [rem_set]*len(remaining)
                self.scrapers_states[scrapers_seen-max_val+self.width].append(seq.copy())
                return
            # Try placing each remaining height
            for val in remaining:
                if val > max_val:
                    generate_states(
                        seq + [val],
                        scrapers_seen + 1,
                        val
                    )
                else:
                    generate_states(
                        seq + [val],
                        scrapers_seen,
                        max_val
                    )
        def is_block(vs, i, j):
            block_sets = [set(v[i:j]) for v in vs]
            target = block_sets[0]

            if any(s != target for s in block_sets):
                return False

            return True

        def collapse(vectors):
            collapsed = False
            if not vectors:
                return []
            n = len(vectors[0])
            result = []
            vec = 0
            while vec < len(vectors):
                vec_updated = False
                for l in range(n,1,-1):
                    if factorial(l) > len(vectors):
                        continue
                    for i in range(0, n - l + 1):
                        # find vectors supporting this block
                        if any(type(v) == set for v in vectors[vec][i:i+l]):
                            continue
                        supporting = []
                        upper_vec = 0
                        for v in vectors[vec:]:
                            upper_vec += 1

                            if all(
                                v[k] == vectors[vec][k]
                                for k in range(n) if k < i or k >= i+l
                            ) and all(
                                type(v[k]) != set
                                for k in range(n) if i <= k < i+l
                            ):
                                supporting.append(v)
                            elif v[:i] != vectors[vec][:i]:
                                break

                        if len(supporting) != factorial(l):
                            continue

                        if is_block(supporting, i, i+l):
                            row = []
                            block = set(supporting[0][i:i+l])
                            for k in range(n):
                                if i <= k < i+l:
                                    row.append(block)
                                else:
                                    row.append(supporting[0][k])
                            result.append(row)
                            vectors[vec:vec+upper_vec] = [v for v in vectors[vec:vec+upper_vec] if v not in supporting]
                            collapsed = True
                            vec_updated = True
                            break
                    if vec_updated:
                        break
                if not vec_updated:
                    vec += 1

            # add singletons
            result.extend(vectors)
            if collapsed:
                return collapse(result)
            for row in vectors:
                for i in range(len(row)):
                    if type(row[i]) == int:
                        row[i] = {row[i]}
            return result

        generate_states()
        self.scrapers_states_collabsed= [collapse(self.scrapers_states[i]) for i in range(self.width+1)]

    # ---------------- Skyscraper helpers ----------------

    def visible_count(self, seq):
        max_seen = 0
        count = 0
        for x in seq:
            if x > max_seen:
                max_seen = x
                count += 1
        return count

    def check_row_clues(self, r):
        row = self.board[r]

        if 0 in row:
            return True  # partial row → cannot fully check

        if self.left_clues[r]:
            if self.visible_count(row) != self.left_clues[r]:
                return False

        if self.right_clues[r]:
            if self.visible_count(row[::-1]) != self.right_clues[r]:
                return False

        return True

    def check_col_clues(self, c):
        col = [self.board[r][c] for r in range(self.height)]

        if 0 in col:
            return True

        if self.upper_clues[c]:
            if self.visible_count(col) != self.upper_clues[c]:
                return False

        if self.lower_clues[c]:
            if self.visible_count(col[::-1]) != self.lower_clues[c]:
                return False

        return True

    # ---------------- Core solver ----------------

    def solve(self):
        possible_values_cache = {}
        cells_to_fill = []

        for i in range(self.height):
            for j in range(self.width):
                if self.board[i][j] == 0:
                    cells_to_fill.append((i, j))

        def is_valid(num, row, col):
            # row uniqueness
            if num in self.board[row]:
                return False

            # column uniqueness
            for r in range(self.height):
                if self.board[r][col] == num:
                    return False

            self.board[row][col] = num
            ok = self.check_row_clues(row) and self.check_col_clues(col)
            self.board[row][col] = 0

            return ok

        def possible_values(row, col):
            N = self.width
            upper_bound = N

            # ---- row: left clue ----
            clue = self.left_clues[row]
            if clue:
                pos = col
                upper_bound = min(upper_bound, N - (clue - 1) + pos)

            # ---- row: right clue ----
            clue = self.right_clues[row]
            if clue:
                pos = N - 1 - col
                upper_bound = min(upper_bound, N - (clue - 1) + pos)

            # ---- column: upper clue ----
            clue = self.upper_clues[col]
            if clue:
                pos = row
                upper_bound = min(upper_bound, N - (clue - 1) + pos)

            # ---- column: lower clue ----
            clue = self.lower_clues[col]
            if clue:
                pos = N - 1 - row
                upper_bound = min(upper_bound, N - (clue - 1) + pos)

            if upper_bound < 1:
                possible_values_cache[(row, col)] = set()
                return []

            values = set(range(1, upper_bound + 1))

            # uniqueness constraints
            values -= set(self.board[row])
            values -= {self.board[r][col] for r in range(self.height)}

            possible_values_cache[(row, col)] = values
            return list(values)

        def possible_values_extended(row, col):
            return list(possible_values_cache[(row, col)])

        def possible_values_trim():
            updated = 0
            N = self.width
            def check_scrapers_states(clue, pos_vals):
                all_pos = [x for x in
                    self.scrapers_states_collabsed[clue] 
                    if all(x[j] & pos_vals[j] for j in range(len(x)))]
                new_pos_vals = [set() for _ in range(len(pos_vals))]
                for v in all_pos:
                    for i in range(len(v)):
                        new_pos_vals[i]|=v[i] & pos_vals[i]
                return new_pos_vals




            # hidden singles (rows)
            for r in range(self.height):
                num_positions = {n: [] for n in range(1, self.width + 1)}
                for c in range(self.width):
                    if (r, c) in possible_values_cache:
                        for n in possible_values_cache[(r, c)]:
                            num_positions[n].append((r, c))
                for n, cells in num_positions.items():
                    if len(cells) == 1:
                        cell = cells[0]
                        if possible_values_cache[cell] != {n}:
                            possible_values_cache[cell] = {n}
                            updated += 1

            # hidden singles (columns)
            for c in range(self.width):
                num_positions = {n: [] for n in range(1, self.width + 1)}
                for r in range(self.height):
                    if (r, c) in possible_values_cache:
                        for n in possible_values_cache[(r, c)]:
                            num_positions[n].append((r, c))
                for n, cells in num_positions.items():
                    if len(cells) == 1:
                        cell = cells[0]
                        if possible_values_cache[cell] != {n}:
                            possible_values_cache[cell] = {n}
                            updated += 1

            # naked subsets (rows & columns)
            Kmax = 3

            for r in range(self.height):
                unit = [(r, c) for c in range(self.width) if (r, c) in possible_values_cache]
                for k in range(1, min(Kmax, len(unit)) + 1):
                    for combo in combinations(unit, k):
                        union_vals = set().union(*(possible_values_cache[x] for x in combo))
                        if len(union_vals) == k:
                            for cell in unit:
                                if cell not in combo:
                                    before = set(possible_values_cache[cell])
                                    after = before - union_vals
                                    if after != before:
                                        possible_values_cache[cell] = after
                                        updated += 1

            for c in range(self.width):
                unit = [(r, c) for r in range(self.height) if (r, c) in possible_values_cache]
                for k in range(1, min(Kmax, len(unit)) + 1):
                    for combo in combinations(unit, k):
                        union_vals = set().union(*(possible_values_cache[x] for x in combo))
                        if len(union_vals) == k:
                            for cell in unit:
                                if cell not in combo:
                                    before = set(possible_values_cache[cell])
                                    after = before - union_vals
                                    if after != before:
                                        possible_values_cache[cell] = after
                                        updated += 1
            # ---------- visibility bounds (dead-state detection) ----------
            for r in range(self.height):
                row = [possible_values_cache[(r, c)] if (r,c) in possible_values_cache else {self.board[r][c]} for c in range(self.width)]

                if self.left_clues[r]:
                    updated_states = check_scrapers_states( self.left_clues[r], row)
                    for c in range(self.width):
                        if (r,c) in possible_values_cache:
                            possible_values_cache[(r,c)]=updated_states[c]
                            if not updated_states[c]:
                                return 0

                if self.right_clues[r]:
                    updated_states = check_scrapers_states( self.right_clues[r], row[::-1])
                    updated_states = updated_states[::-1]
                    for c in range(self.width):
                        if (r,c) in possible_values_cache:
                            possible_values_cache[(r,c)]=updated_states[c]
                            if not updated_states[c]:
                                return 0

            for c in range(self.width):
                col = [possible_values_cache[(r, c)] if (r,c) in possible_values_cache else {self.board[r][c]} for r in range(self.height)]

                if self.upper_clues[c]:
                    updated_states = check_scrapers_states( self.upper_clues[c], col)
                    for r in range(self.height):
                        if (r,c) in possible_values_cache:
                            possible_values_cache[(r,c)]=updated_states[r]
                            if not updated_states[r]:
                                return 0
                if self.lower_clues[c]:
                    updated_states = check_scrapers_states( self.lower_clues[c], col[::-1])
                    updated_states = updated_states[::-1]
                    for r in range(self.height):
                        if (r,c) in possible_values_cache:
                            possible_values_cache[(r,c)]=updated_states[r]
                            if not updated_states[r]:
                                return 0

            return updated
        
        def solve_skyscrapers(idx=0):
            if idx >= len(cells_to_fill):
                return True

            possible_values_cache.clear()

            cells_to_fill[idx:] = sorted(
                cells_to_fill[idx:],
                key=lambda x: len(possible_values(x[0], x[1]))
            )

            while possible_values_trim():
                pass
            cells_to_fill[idx:] = sorted(
                cells_to_fill[idx:],
                key=lambda x: len(possible_values_extended(x[0], x[1]))
            )
            i, j = cells_to_fill[idx]
            pos_lst =list(possible_values_cache.get((i, j), range(1, self.width + 1)))
            for num in pos_lst:
                if is_valid(num, i, j):
                    self.board[i][j] = num
                    if solve_skyscrapers(idx + 1):
                        return True
                    self.board[i][j] = 0

            return False

        solve_skyscrapers()
        print(self.board)
        return self.board
