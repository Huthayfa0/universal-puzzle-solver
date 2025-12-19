from math import sqrt

def extract_task(driver):
    """
    Tries to read window.task (string).
    Returns Python dictionary.
    """
    info = {}
    info["puzzle"] = driver.current_url.split("/")[3]
    info["type"] = driver.current_url.split("/")[-1]
    raw_task = driver.execute_script("return Settings.bag;")

    if not raw_task:
        raise ValueError("No 'task' variable found on page.")

    for keys in raw_task:
        if ".save." in keys:
            info["task"] = raw_task[keys]["task"]
            return info
    
    raise ValueError("No valid task data found in 'task' variable.")

class TaskParserBase:
    def __init__(self, info={}):
        self.info = info

    def parse(self, raw_task):
        raise NotImplementedError("This method should be overridden by subclasses.")

class TableTaskParser(TaskParserBase):
    def parse(self, raw_task):
        # Example parsing logic for table-based tasks
        task_data = {}
        table = []
        char_idx = 0
        while char_idx in range(len(raw_task)):
            char = raw_task[char_idx]
            if char == 'W' or char == 'B':
                table.append(char)
            elif char.isdigit():
                char_start = char_idx
                while (char_idx + 1 < len(raw_task)) and raw_task[char_idx + 1].isdigit():
                    char_idx += 1
                number = int(raw_task[char_start:char_idx + 1])
                table.append(number)
            elif char == '_':
                pass
            else:
                table.extend([0] * (ord(char) - ord('a') + 1))
            char_idx += 1
        if self.info.get("height") is not None:
            task_data["height"] = self.info.get("height")
        else:
            task_data["height"] = int(sqrt(len(table)))
        task_data["width"] = len(table) // task_data["height"]
        task_data["table"] = [
            table[i:i + int(task_data["width"])]
            for i in range(0, len(table), int(task_data["width"]))
        ]
        return task_data

class BoxesTaskParser(TaskParserBase):
    def parse_cell(self, s):
        return int(s)-1
    def parse(self, raw_task):
        # Example parsing logic for table-based tasks
        task_data = {}
        table = list(map(self.parse_cell ,raw_task.split(",")))
        if self.info.get("height") is not None:
            task_data["height"] = self.info.get("height")
        else:
            task_data["height"] = int(sqrt(len(table)))
        task_data["width"] = len(table) // task_data["height"]
        task_data["boxes_table"] = [
            table[i:i + int(task_data["width"])]
            for i in range(0, len(table), int(task_data["width"]))
        ]
        boxes=[]
        boxes_borders=[]
        for i in range(task_data["height"]):
            for j in range(task_data["width"]):
                v = task_data["boxes_table"][i][j]
                while v>=len(boxes):
                    boxes.append([])
                    boxes_borders.append({})
                boxes[v].append((i,j))
                for dir in [(1,0),(-1,0),(0,1),(0,-1)]:
                    if 0<=i+dir[0] <task_data["height"] and 0<=j+dir[1] <task_data["width"]:
                        v2= task_data["boxes_table"][i+dir[0]][j+dir[1]]
                        if v!= v2:
                            boxes_borders[v].setdefault(v2,[])
                            boxes_borders[v][v2].append((i,j,dir))
        task_data["boxes"]=boxes
        task_data["boxes_borders"]=boxes_borders
        return task_data

class BorderTaskParser(TaskParserBase):
    def parse(self, raw_task):
        # Example parsing logic for table-based tasks
        task_data = {}
        if '.' in raw_task:
            border = list(map(lambda x: x if x.isdigit() else x, raw_task.split('/')))
            border = [list(map(lambda y: int(y) if y.isdigit() else y, x.split('.'))) for x in border]
        else:
            border = list(map(lambda x: int(x) if x.isdigit() else x, raw_task.split('/')))
        
        if self.info.get("height") is not None:
            task_data["height"] = self.info.get("height")
        else:
            task_data["height"] = len(border) // 2
        task_data["width"] = len(border) - task_data["height"]
        task_data["vertical_borders"] = border[:task_data["width"]] # up or down values
        task_data["horizontal_borders"] = border[task_data["width"]:] # left or right values
        return task_data

class CellTableTaskParser(TaskParserBase):
    def parse_number(self, s):
        num = ""
        for char in s:
            if char.isdigit():
                num += char
            else:
                break
        return int(num) if num else None

    def parse_letters(self, s):
        letters = []
        for char in s:
            if char.isalpha():
                if char == 'D':
                    letters.append((1,0))
                elif char == 'U':
                    letters.append((-1,0))
                elif char == 'R':
                    letters.append((0,1))
                elif char == 'L':
                    letters.append((0,-1))

        return letters
    def parse(self, raw_task):
        # Example parsing logic for table-based tasks
        task_data = {}
        table = list(map(self.parse_number ,raw_task.split(",")))
        cell_table = list(map(self.parse_letters ,raw_task.split(",")))
        if self.info.get("height") is not None:
            task_data["height"] = self.info.get("height")
        else:
            task_data["height"] = int(sqrt(len(table)))
        task_data["width"] = len(table) // task_data["height"]
        task_data["table"] = [
            table[i:i + int(task_data["width"])]
            for i in range(0, len(table)-1, int(task_data["width"]))
        ]
        task_data["cell_info_table"] = [
            cell_table[i:i + int(task_data["width"])]
            for i in range(0, len(cell_table)-1, int(task_data["width"]))
        ]
        
        return task_data