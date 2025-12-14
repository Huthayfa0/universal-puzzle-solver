from .solver import BaseSolver
from math import comb
from copy import copy, deepcopy
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from threading import Event

class NonogramsSolver(BaseSolver):
    def __init__(self, info):
        super().__init__(info)
        self.row_info = self.info["horizontal_borders"]
        self.col_info = self.info["vertical_borders"]
        self.height = self.info["height"]
        self.width = self.info["width"]
        self.board = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.clues_order = []
        self.first_possible_value_line_cache = {}

    def possible_values_expected_heuristic(self,clues, length):
        if not clues:
            return 1  # all empty
        free = length - (sum(clues) + len(clues) - 1)
        if free < 0:
            return 0
        return comb(free + len(clues), len(clues))

    def possible_values_line_with_heur(self, arr,val,index=0,min_heuristic=0,max_heuristic=-1):
        results = []

        remaining_len = len(arr) - index
        upper_bound = self.possible_values_expected_heuristic(val, remaining_len)

        if upper_bound == 0:
            return []

        if upper_bound < min_heuristic:
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
                        arr,
                        val,
                        index + block + (index + block < len(arr)),
                        min_heuristic,
                        max_heuristic
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
                arr,
                val,
                index + 1,
                min_heuristic,
                max_heuristic
            )
        )
        arr[index] = 0

        if max_heuristic != -1:
            return results[:max_heuristic]

        return results


    def possible_values_line(self, arr,val,index=0,order=0):
        results = []
        if index >= len(arr):
            if val == []:
                results.append(arr.copy())
            return results
        if val == []:
            if any(x == 1 for x in arr[index:]):
                return []
            else:
                if arr[index]==2:
                    return self.possible_values_line(arr, val, index + 1)
                arr[index] = 2
                results.extend(self.possible_values_line(arr, val, index + 1))
                arr[index] = 0
                return results
        if index + sum(val) + len(val) - 1 > len(arr):
            return []
        if arr[index]==2:
            return self.possible_values_line(arr, val, index + 1)
        if all(x != 2 for x in arr[index:index + val[0]]) and (index + val[0] == len(arr) or arr[index + val[0]] != 1):
            tmp_arr = arr[index:index + val[0] + (index + val[0] != len(arr))].copy()
            for i in range(val[0]):
                arr[index + i] = 1
            if index + val[0] != len(arr):
                arr[index + val[0]] = 2
            tmp=val.pop(0)
            results.extend(self.possible_values_line(arr, val, index + tmp + (index + tmp < len(arr))))
            val.insert(0,tmp)
            arr[index:index + val[0] + (index + val[0] != len(arr))] = tmp_arr
        if arr[index]==1:
            return results
        if len(results)>order: #this is added for it to end early
            return results[:order+1]
        arr[index] = 2
        results.extend(self.possible_values_line(arr, val, index + 1,order-len(results)))
        arr[index] = 0
        return results[:order+1]
    
    def decode(self,arr):
        v=1
        s=0
        for x in arr:
            s+=x*v
            v*=3 
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
        cache_key=(0)
        if len(arr)-index<=16:
            cache_key =(len(arr)-index,self.decode(arr[index:]),*val)

        if len(arr)-index<=16 and cache_key in self.first_possible_value_line_cache:
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
            f_right = executor.submit(
                worker,
                list(reversed(arr)),
                list(reversed(val))
            )

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
        s = self.submit_common()
        while s > 0:
            print("Solving common:",s)
            s = self.submit_common()
        board_copy =[[]]*(self.height+self.width)
        diff = 1000
        cached = [0]*(self.height+self.width)
        processed_cache = [0]*(self.height+self.width)
        possible_vals_db= [[]]*(self.height+self.width)
        clue_idx = 0
        while clue_idx < self.height + self.width:
            cell_idx = self.clues_order[clue_idx]
            clue = self.row_info[cell_idx[0]] if cell_idx[1]=="row" else self.col_info[cell_idx[0]]
            clue_len = self.width if cell_idx[1]=="row" else self.height
            line = self.board[cell_idx[0]] if cell_idx[1]=="row" else [a[cell_idx[0]] for a in self.board]
            if processed_cache[clue_idx]>=self.possible_values_expected_heuristic(clue,clue_len):
                processed_cache[clue_idx]=0
                cached[clue_idx]=0
                possible_vals_db[clue_idx]=[]
                board_copy[clue_idx]=[]
                clue_idx-=1
                self.board=board_copy[clue_idx]
                print("Back tracking clue:", cell_idx)
                continue
            if all(x!=0 for x in line):
                clue_idx+=1
                continue
            if cached[clue_idx]<=processed_cache[clue_idx] or not possible_vals_db[clue_idx]:
                possible_vals_db[clue_idx]= self.possible_values_line_with_heur(line,clue,0,cached[clue_idx],cached[clue_idx]+diff)
                cached[clue_idx]+=diff
            if processed_cache[clue_idx] % diff >=len(possible_vals_db[clue_idx]):
                processed_cache[clue_idx]=cached[clue_idx]
                continue
            print("Trying value for clue:",clue_idx,cell_idx,"heuristic:",processed_cache[clue_idx])
            board_copy[clue_idx] = deepcopy(self.board)
            if cell_idx[1]=="row":
                self.board[cell_idx[0]] = possible_vals_db[clue_idx][processed_cache[clue_idx] % diff]
            else:
                for i in range(len(self.board)):
                    self.board[i][cell_idx[0]] = possible_vals_db[clue_idx][processed_cache[clue_idx] % diff][i]

            processed_cache[clue_idx]+=1
            s = self.submit_common()
            while s > 0:
                print("Solving common:",s)
                s = self.submit_common()
            if s!=-1:
                clue_idx += 1
            else:
                self.board=board_copy[clue_idx]
        return self.is_valid()
    def solve(self):
        self.clues_order = [(i, 'row') for i in range(self.height)] + [(j, 'col') for j in range(self.width)]
        self.clues_order = sorted(self.clues_order, key=lambda x: self.possible_values_expected_heuristic(self.row_info[x[0]],self.width)
                                  if x[1]=='row' else self.possible_values_expected_heuristic(self.col_info[x[0]],self.height))
        self.solve_puzzle()
        print(self.board)
        return self.board