from .solver import BaseSolver
from math import comb
from copy import copy, deepcopy
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from threading import Event
from itertools import chain


class NonogramsSolver(BaseSolver):
    """Solver for Nonograms (Picross) puzzles.
    
    Nonograms require filling cells to match row and column clues indicating
    consecutive filled blocks. Uses advanced constraint propagation and backtracking.
    """
    
    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        """Initialize the Nonograms solver.
        
        Args:
            info: Dictionary containing:
                - horizontal_borders: Row clues (lists of block lengths)
                - vertical_borders: Column clues (lists of block lengths)
                - height, width: Puzzle dimensions
            show_progress: If True, show progress updates during solving.
            partial_solution_callback: Optional callback to display partial solution.
            progress_interval: Interval in seconds for progress updates (default: 10.0).
            partial_interval: Interval in seconds for partial solution display (default: 100.0).
        """
        super().__init__(info, show_progress=show_progress, partial_solution_callback=partial_solution_callback,
                        progress_interval=progress_interval, partial_interval=partial_interval)
        self.row_info = self.info["horizontal_borders"]
        self.col_info = self.info["vertical_borders"]
        self.height = self.info["height"]
        self.width = self.info["width"]
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.clues_order = []  # Order for processing clues
        self.first_possible_value_line_cache = {}  # Cache for line solving

    def possible_values_expected_heuristic(self, clues, length):
        """Calculate the expected number of possible line configurations.
        
        Used as a heuristic to estimate search space size.
        
        Args:
            clues: List of block lengths
            length: Line length
        
        Returns:
            Estimated number of configurations.
        """
        if not clues:
            return 1  # All empty
        
        free = length - (sum(clues) + len(clues) - 1)
        if free < 0:
            return 0
        return comb(free + len(clues), len(clues))

    def possible_values_line_with_heur(self, arr,val,index=0,min_heuristic=0,max_heuristic=-1):
        results = []
        remaining_len = len(arr) - index
        upper_bound = self.possible_values_expected_heuristic(val, remaining_len)
        if upper_bound == 0 or upper_bound < min_heuristic:
            return []
        if index >= len(arr):
            if not val:
                results.append(arr.copy())
            return results
        if not val:
            if any(x == 1 for x in arr[index:]):
                return []
            else:
                if arr[index] == 2:
                    return self.possible_values_line_with_heur(
                        arr, val, index + 1, min_heuristic, max_heuristic
                    )
                arr[index] = 2
                results.extend(
                    self.possible_values_line_with_heur(
                        arr, val, index + 1, min_heuristic, max_heuristic
                    )
                )
                arr[index] = 0
                return results

        if index + sum(val) + len(val) - 1 > len(arr):
            return []

        if arr[index] == 2:
            return self.possible_values_line_with_heur(
                arr, val, index + 1, min_heuristic, max_heuristic
            )
        heuristic1_lim=self.possible_values_expected_heuristic(val[1:],len(arr)-(index + val[0] + (index + val[0] < len(arr))))
        # --- Try placing block ---
        if arr[index] == 1 or min_heuristic <= heuristic1_lim:
            if (
                all(x != 2 for x in arr[index:index + val[0]])
                and (index + val[0] >= len(arr) or arr[index + val[0]] != 1)
            ):
                tmp_arr = arr[index:index + val[0] + (index + val[0] != len(arr))].copy()

                for i in range(val[0]):
                    arr[index + i] = 1
                if index + val[0] != len(arr):
                    arr[index + val[0]] = 2

                block = val.pop(0)
                results.extend(
                    self.possible_values_line_with_heur(
                        arr, val,
                        index + block + (index + block < len(arr)),
                        min_heuristic, max_heuristic
                    )
                )
                
                val.insert(0, block)

                arr[index:index + len(tmp_arr)] = tmp_arr

            if arr[index] == 1:
                return results
        min_heuristic -= heuristic1_lim
        max_heuristic -= heuristic1_lim
        # --- Try empty cell ---
        if min_heuristic<=0:
            min_heuristic = 0
        if max_heuristic <=0:
            return results
        arr[index] = 2
        results.extend(
            self.possible_values_line_with_heur(
                arr, val,
                index + 1,
                min_heuristic, max_heuristic
            )
        )
        arr[index] = 0

        if max_heuristic != -1:
            return results[:max_heuristic]

        return results

    def decode(self, arr):
        """Decode a line state array into a cache key.
        
        Args:
            arr: Line state array (0=unknown, 1=filled, 2=empty)
        
        Returns:
            Integer cache key.
        """
        v = 1
        s = 0
        for x in arr:
            s += x * v
            v *= 3
        return s

    def first_possible_value_line(self, arr, val, index=0):
        # Base case: reached end
        
        if index >= len(arr):
            return [] if not val else None

        # No more blocks to place
        if not val:
            # remaining cells must not contain forced 1s
            if any(x == 1 for x in arr[index:]):
                return None
            for i in range(index, len(arr)):
                if arr[i] == 0:
                    arr[i] = 2
            return arr[index:]

        # Prune: not enough space left
        if index + sum(val) + len(val) - 1 > len(arr):
            return None

        # Skip forced empty
        if arr[index] == 2:
            res= self.first_possible_value_line(arr, val, index + 1)
            if res is None: 
                return None
            arr[index+1:]= res
            return arr[index:].copy()

        block_len = val[0]

        # Placing block
        if arr[index] == 1:
            if (
                arr[index] == 1 and
                all(arr[index + i] != 2 for i in range(block_len)) and
                (index + block_len == len(arr) or arr[index + block_len] != 1)
            ):
                backup = arr[index:index + block_len + (index + block_len < len(arr))].copy()
                for i in range(block_len):
                    arr[index + i] = 1
                if index + block_len < len(arr):
                    arr[index + block_len] = 2
    
                res = self.first_possible_value_line(
                    arr,
                    val[1:],
                    index + block_len + (index + block_len < len(arr))
                )
                if res is not None:
                    arr[index + block_len + (index + block_len < len(arr)):] = res
                    return arr[index:]
    
                # rollback
                arr[index:index + block_len + (index + block_len < len(arr))] = backup
                if res is None:
                    return None
            else:
                return None   
        cache_key = (len(arr) - index, self.decode(arr[index:]), *val)

        if cache_key in self.first_possible_value_line_cache:
            if self.first_possible_value_line_cache[cache_key] is None:
                return None
            arr[index:]=self.first_possible_value_line_cache[cache_key].copy()
            return arr[index:]
        # Placing block
        if (
            all(arr[index + i] != 2 for i in range(block_len)) and
            (index + block_len == len(arr) or arr[index + block_len] != 1)
        ):
            backup = arr[index:index + block_len + (index + block_len < len(arr))].copy()
            for i in range(block_len):
                arr[index + i] = 1
            if index + block_len < len(arr):
                arr[index + block_len] = 2

            res = self.first_possible_value_line(
                arr,
                val[1:],
                index + block_len + (index + block_len < len(arr))
            )
            if res is not None:
                arr[index + block_len + (index + block_len < len(arr)):] = res
                self.first_possible_value_line_cache[cache_key] =arr[index:].copy()
                return arr[index:]

            # rollback
            arr[index:index + block_len + (index + block_len < len(arr))] = backup
        # Try marking empty
        arr[index] = 2
        res = self.first_possible_value_line(arr, val, index + 1)
        if res is not None:
            arr[index+1:]=res
            self.first_possible_value_line_cache[cache_key] =arr[index:].copy()
            return arr[index:]
        arr[index] = 0
        self.first_possible_value_line_cache[cache_key] =None
        return None

    def possible_values_line_fork_join(self, arr, val):
        stop_event = Event()

        def worker(a, v):
            if stop_event.is_set():
                return None
            result = self.first_possible_value_line(a, v)
            if result is None:
                stop_event.set()   # fail fast
            return result

        with ThreadPoolExecutor(max_workers=2) as executor:
            f_left = executor.submit(worker, arr.copy(), val.copy())
            f_right = executor.submit( worker, list(reversed(arr)),  list(reversed(val)) )
            futures = {f_left, f_right}
            results = {}
            while futures:
                done, futures = wait(futures, return_when=FIRST_COMPLETED)
                for f in done:
                    res = f.result()
                    # ❌ Fail fast
                    if res is None:
                        stop_event.set()
                        for pending in futures:
                            pending.cancel()
                        return None
                    results[f] = res

            # ✅ Both succeeded
            return results[f_left], results[f_right] 
    def common_values_line(self,arr, val):
        res_pos=self.possible_values_line_fork_join(arr,val)
        if res_pos is None:
            return None
        possible_lines_l, possible_lines_r = res_pos
        possible_lines_r=list(reversed(possible_lines_r))
        common = arr.copy()
        clue_p_l = 0
        clue_p_r = 0
        clue_p_l_cnt = 0
        clue_p_r_cnt = 0
        for i in range(len(arr)):
            if possible_lines_l[i] == 1 and possible_lines_r[i] == 1:
                if clue_p_l == clue_p_r:
                    common[i] = 1
            elif possible_lines_l[i] == 2 and possible_lines_r[i] == 2:
                if clue_p_l == clue_p_r:
                    common[i] = 2
            if possible_lines_l[i]==1:
                clue_p_l_cnt+=1
                if clue_p_l_cnt==val[clue_p_l]:
                    clue_p_l+=1
                    clue_p_l_cnt=0
            if possible_lines_r[i]==1:
                clue_p_r_cnt+=1
                if clue_p_r_cnt==val[clue_p_r]:
                    clue_p_r+=1
                    clue_p_r_cnt=0
        for i in range(len(arr)):
            if common[i]!=0:
                continue
            common[i]=1
            if self.first_possible_value_line(common.copy(),val) is None:
                common[i]=2
                continue
            common[i]=2
            if self.first_possible_value_line(common.copy(),val) is None:
                common[i]=1
                continue
            common[i]=0
        return common   
        

    def is_valid(self):
        # Check row vals
        for i in range(self.height):
            tmp_arr = [0]
            for j in range(self.width):
                if self.board[i][j] == 1:
                    tmp_arr[-1] += 1
                elif self.board[i][j] == 2:
                    if tmp_arr[-1] != 0:
                        tmp_arr.append(0)
            if tmp_arr[-1] == 0:
                tmp_arr.pop()
            if tmp_arr != self.row_info[i]:
                return False
        # Check column vals
        for j in range(self.width):
            tmp_arr = [0]
            for i in range(self.height):
                if self.board[i][j] == 1:
                    tmp_arr[-1] += 1
                elif self.board[i][j] == 2:
                    if tmp_arr[-1] != 0:
                        tmp_arr.append(0)
            if tmp_arr[-1] == 0:
                tmp_arr.pop()
            if tmp_arr != self.col_info[j]:
                return False
        return True


    def submit_common(self):
        updated = 0
        for idx, line_type in self.clues_order:
            if line_type == 'row':
                common = self.common_values_line(self.board[idx], self.row_info[idx])
                if common is not None:
                    for j in range(self.width):
                        if common[j] != 0 and self.board[idx][j] != common[j]:
                            self.board[idx][j] = common[j]
                            updated += 1
                else:
                    return -1
            else:  # line_type == 'col'
                col = [self.board[i][idx] for i in range(self.height)]
                common = self.common_values_line(col, self.col_info[idx])
                if common is not None:
                    for i in range(self.height):
                        if common[i] != 0 and self.board[i][idx] != common[i]:
                            self.board[i][idx] = common[i]
                            updated += 1
                else: 
                    return -1
        return updated
    
    def solve_puzzle(self):
        """Solve using constraint propagation and backtracking with clue ordering.
        
        Returns:
            True if puzzle is solved, False otherwise.
        """
        s = self.submit_common()
        while s > 0:
            s = self.submit_common()
        
        # Backtracking state
        board_copy = [[]] * (self.height + self.width)
        diff = 1000  # Batch size for possible values
        cached = [0] * (self.height + self.width)
        processed_cache = [0] * (self.height + self.width)
        possible_vals_db = [[]] * (self.height + self.width)
        
        total_clues = len(self.clues_order)
        clue_idx = 0
        while clue_idx < self.height + self.width:
            cell_idx = self.clues_order[clue_idx]
            clue = self.row_info[cell_idx[0]] if cell_idx[1] == "row" else self.col_info[cell_idx[0]]
            clue_len = self.width if cell_idx[1] == "row" else self.height
            line = self.board[cell_idx[0]] if cell_idx[1] == "row" else [a[cell_idx[0]] for a in self.board]
            
            # Backtrack if we've exhausted all possibilities for this clue
            if processed_cache[clue_idx] >= self.possible_values_expected_heuristic(clue, clue_len):
                processed_cache[clue_idx] = 0
                cached[clue_idx] = 0
                possible_vals_db[clue_idx] = []
                board_copy[clue_idx] = []
                clue_idx -= 1
                while not board_copy[clue_idx]:
                    clue_idx -= 1
                self.board = board_copy[clue_idx]
                continue
            
            # Update progress
            self._update_progress(
                clue_idx=clue_idx,
                total_clues=total_clues,
                clue_type=cell_idx[1] if clue_idx < len(self.clues_order) else "",
                cells_filled=sum(1 for row in self.board for cell in row if cell != 0),
                total_cells=self.height * self.width
            )
            
            # Skip if line is already complete
            if all(x != 0 for x in line):
                clue_idx += 1
                continue
            
            # Load possible values if needed
            if cached[clue_idx] <= processed_cache[clue_idx] or not possible_vals_db[clue_idx]:
                possible_vals_db[clue_idx] = self.possible_values_line_with_heur(
                    line, clue, 0, cached[clue_idx], cached[clue_idx] + diff
                )
                cached[clue_idx] += diff
            
            # Check if we've exhausted current batch
            if processed_cache[clue_idx] % diff >= len(possible_vals_db[clue_idx]):
                processed_cache[clue_idx] = cached[clue_idx]
                continue
            
            # Try next possible value
            board_copy[clue_idx] = deepcopy(self.board)
            if cell_idx[1] == "row":
                self.board[cell_idx[0]] = possible_vals_db[clue_idx][processed_cache[clue_idx] % diff]
            else:
                for i in range(len(self.board)):
                    self.board[i][cell_idx[0]] = possible_vals_db[clue_idx][processed_cache[clue_idx] % diff][i]

            processed_cache[clue_idx] += 1
            s = self.submit_common()
            while s > 0:
                s = self.submit_common()
            
            if s != -1:
                clue_idx += 1
            else:
                self.board = board_copy[clue_idx]
        
        return self.is_valid()
    def solve(self):
        """Solve the Nonograms puzzle.
        
        Builds a processing order for clues (alternating rows and columns from edges),
        then solves using constraint propagation and backtracking.
        
        Returns:
            2D list representing the solved puzzle board.
        """
        self._start_progress_tracking()
        
        self.clues_order = []
        rL, rR = 0, self.height
        cL, cR = 0, self.width
        
        # Build clue processing order: process edges first
        while rL < rR or cL < cR:
            # Process 3 rows from left
            for i in range(rL, min(rL + 3, rR)):
                self.clues_order.append((i, 'row'))
            rL += 3
            
            # Process 3 rows from right
            for i in range(rR - 1, max(rR - 4, rL - 1), -1):
                self.clues_order.append((i, 'row'))
            rR -= 3
            
            # Process 3 columns from top
            for j in range(cL, min(cL + 3, cR)):
                self.clues_order.append((j, 'col'))
            cL += 3
            
            # Process 3 columns from bottom
            for j in range(cR - 1, max(cR - 4, cL - 1), -1):
                self.clues_order.append((j, 'col'))
            cR -= 3
        
        try:
            self.solve_puzzle()
        finally:
            self._stop_progress_tracking()
        
        return self.board
