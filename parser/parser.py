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
    def parse(self, raw_task, height=None):
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
        if height is not None:
            task_data["height"] = height
        else:
            task_data["height"] = int(sqrt(len(table)))
        task_data["width"] = len(table) // task_data["height"]
        task_data["table"] = [
            table[i:i + int(task_data["width"])]
            for i in range(0, len(table), int(task_data["width"]))
        ]
        return task_data
