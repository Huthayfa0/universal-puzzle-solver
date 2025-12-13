from .kakurasu_solver import KakurasuSolver

class NonogramsSolver(KakurasuSolver):
    def possible_values_line(self, arr,val,index=0,order=0):
        # print(f"Calculating possible values for arr {arr} for map {val} at index {index}")
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
            tmp_arr = arr[index:index + val[0] + (index + val[0] != len(arr))]
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
                        
    def common_values_line(self,arr, val):
        possible_lines_l = self.possible_values_line(arr.copy(), val)
        if not possible_lines_l:
            return None
        possible_lines_r = self.possible_values_line(list(reversed(arr)), list(reversed(val)))
        possible_lines_l=possible_lines_l[0]
        possible_lines_r=list(reversed(possible_lines_r[0]))
        common = arr.copy()
        # print ("Possible lines:", possible_lines, "for val", val, "and arr", arr)
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
        lines = [(i, 'row') for i in range(self.height)] + [(j, 'col') for j in range(self.width)]
        lines = [line for line in lines if not (
            (line[1] == 'row' and all(v == 0 for v in self.board[line[0]]) and sum(self.row_info[line[0]])+len(self.row_info[line[0]])-1 + max(self.row_info[line[0]]) < self.width) or
            (line[1] == 'col' and all(self.board[r][line[0]] == 0 for r in range(self.height)) and sum(self.col_info[line[0]])+len(self.col_info[line[0]])-1 + max(self.col_info[line[0]]) < self.height)
        )]
        lines = sorted(lines, key=lambda x: -(
            sum(self.row_info[x[0]]) + len(self.row_info[x[0]]) - sum(1 for v in self.board[x[0]] if v == 1) + sum(1 for v in self.board[x[0]] if v == 2)
            if x[1] == 'row' else
            sum(self.col_info[x[0]]) + len(self.col_info[x[0]]) - sum(1 for r in range(self.height) if self.board[r][x[0]] == 1) + sum(1 for r in range(self.height) if self.board[r][x[0]] == 2)
        ))
        print("Processing lines in order:", lines)
        for idx, line_type in lines:
            if line_type == 'row':
                common = self.common_values_line(self.board[idx], self.row_info[idx])
                if common is not None:
                    for j in range(self.width):
                        if common[j] != 0 and self.board[idx][j] != common[j]:
                            self.board[idx][j] = common[j]
                            updated += 1
                    print(f"Row {idx} common values: {common}, updated {updated} cells.")
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
                    print(f"Column {idx} common values: {common}, updated {updated} cells.")
                else: 
                    return -1
        return updated
    
    def solve_puzzle(self, cell_idx=0):
        if cell_idx >= self.height:
            return self.is_valid()
        cached=5
        possible_vals= self.possible_values_line(self.board[cell_idx],self.row_info[cell_idx],cached)
        # while possible_vals:
        #     self.board[i][j] = value
        #     if self.solve_puzzle(cell_idx + 1):
        #         return True
        #     self.board[i][j] = 0
        # return False