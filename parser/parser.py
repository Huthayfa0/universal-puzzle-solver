from math import sqrt


class PuzzlePageError(Exception):
    """Exception raised when the current page is not a valid puzzle page."""
    pass


def validate_puzzle_page(driver):
    """Validate that the current page is a valid puzzle page.
    
    Args:
        driver: Selenium WebDriver instance.
    
    Raises:
        PuzzlePageError: If the page is not a valid puzzle page.
    """
    current_url = driver.current_url
    
    # Check if we're on puzzles-mobile.com
    if "puzzles-mobile.com" not in current_url:
        raise PuzzlePageError(
            f"Not on puzzles-mobile.com. Current URL: {current_url}\n"
            "Please navigate to a puzzle page on puzzles-mobile.com"
        )
    
    # Check URL structure - should have puzzle type in path
    url_parts = current_url.split("/")
    if len(url_parts) < 4:
        raise PuzzlePageError(
            f"Invalid URL structure. Current URL: {current_url}\n"
            "Please navigate to a specific puzzle page (e.g., puzzles-mobile.com/sudoku/daily)"
        )
    
    # Check if Settings object exists
    try:
        settings_exists = driver.execute_script("return typeof Settings !== 'undefined';")
        if not settings_exists:
            raise PuzzlePageError(
                "Settings object not found on page. This may not be a puzzle page.\n"
                "Please ensure you're on an active puzzle page."
            )
    except Exception as e:
        raise PuzzlePageError(
            f"Error checking page state: {e}\n"
            "Please ensure you're on a puzzle page and the page has fully loaded."
        ) from e


def extract_task(driver):
    """Extract puzzle task information from the webpage.
    
    Reads the puzzle task from the browser's JavaScript Settings.bag object
    and extracts puzzle type and task data from the current URL and page state.
    
    Args:
        driver: Selenium WebDriver instance pointing to the puzzle page.
    
    Returns:
        dict: Dictionary containing:
            - "puzzle": Puzzle type (e.g., "sudoku", "kakurasu")
            - "type": Puzzle difficulty/variant (e.g., "daily", "weekly")
            - "task": Raw task string to be parsed
    
    Raises:
        PuzzlePageError: If the page is not a valid puzzle page.
        ValueError: If puzzle data cannot be extracted.
    """
    # First validate that we're on a puzzle page
    validate_puzzle_page(driver)
    
    info = {}
    url_parts = driver.current_url.split("/")
    
    # Extract puzzle type from URL
    if len(url_parts) < 4:
        raise PuzzlePageError(
            f"Invalid URL structure. Expected format: puzzles-mobile.com/<puzzle-type>/<difficulty>\n"
            f"Current URL: {driver.current_url}"
        )
    
    info["puzzle"] = url_parts[3]
    info["type"] = url_parts[-1]
    
    # Try to get Settings.bag
    try:
        raw_task = driver.execute_script("return Settings.bag;")
    except Exception as e:
        raise PuzzlePageError(
            f"Error accessing Settings.bag: {e}\n"
            "This may not be a puzzle page, or the page may not have fully loaded."
        ) from e

    if not raw_task:
        raise PuzzlePageError(
            "No puzzle data found on page. Settings.bag is empty or null.\n"
            "Please ensure you're on an active puzzle page with a puzzle loaded."
        )

    # Find task data in Settings.bag
    for key in raw_task:
        if ".save." in key:
            task_data = raw_task[key].get("task")
            if task_data:
                info["task"] = task_data
                return info
    
    raise PuzzlePageError(
        "No valid task data found in Settings.bag.\n"
        "The page may not have a puzzle loaded, or the puzzle format is unsupported."
    )

class TaskParserBase:
    """Base class for all task parsers."""
    
    def __init__(self, info=None):
        """Initialize the parser with puzzle information.
        
        Args:
            info: Dictionary containing puzzle metadata (height, width, type, etc.)
        """
        self.info = info if info is not None else {}

    def parse(self, raw_task):
        """Parse raw task string into structured puzzle data.
        
        Args:
            raw_task: Raw task string from the webpage.
        
        Returns:
            dict: Parsed puzzle data structure.
        
        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

class TableTaskParser(TaskParserBase):
    def parse(self, raw_task):
        """Parse table-based task into a 2D grid structure.
        When info['binary'] is True (e.g. Binairo), digits 0 and 1 are stored as 'W' and 'B'.
        Otherwise, 0 is stored as 2; letter expansion uses 2 (binary) or 0 (non-binary).
        """
        task_data = {}
        table = []
        char_idx = 0
        binary = self.info.get("binary", False)

        while char_idx < len(raw_task):
            char = raw_task[char_idx]
            if char in ('W', 'B'):
                table.append(char)
            elif char.isdigit():
                char_start = char_idx
                while (not binary and char_idx + 1 < len(raw_task)) and raw_task[char_idx + 1].isdigit():
                    char_idx += 1
                number = int(raw_task[char_start:char_idx + 1])
                if binary:
                    # Binary table: 0 → W (white), 1 → B (black)
                    if number == 0:
                        table.append('W')
                    elif number == 1:
                        table.append('B')
                    else:
                        table.append(number)  # e.g. 2 for empty
                else:
                    table.append(2 if number == 0 else number)
            elif char == '_':
                pass  # Skip underscore
            else:
                # Expand letter to multiple zeros (a=1, b=2, etc.)
                table.extend([0] * (ord(char) - ord('a') + 1))
            char_idx += 1
        
        if self.info.get("height") is not None:
            task_data["height"] = self.info.get("height")
        else:
            task_data["height"] = int(sqrt(len(table)))
        task_data["width"] = len(table) // task_data["height"]
        task_data["table"] = [
            table[i:i + task_data["width"]]
            for i in range(0, len(table), task_data["width"])
        ]
        return task_data

class BoxesTaskParser(TaskParserBase):
    def parse_cell(self, s):
        """Parse a single cell value (1-indexed to 0-indexed)."""
        return int(s) - 1
    
    def parse(self, raw_task):
        """Parse box-based task into boxes and borders structure."""
        task_data = {}
        table = list(map(self.parse_cell, raw_task.split(",")))
        
        if self.info.get("height") is not None:
            task_data["height"] = self.info.get("height")
        else:
            task_data["height"] = int(sqrt(len(table)))
        task_data["width"] = len(table) // task_data["height"]
        task_data["boxes_table"] = [
            table[i:i + task_data["width"]]
            for i in range(0, len(table), task_data["width"])
        ]
        
        boxes = []
        boxes_borders = []
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        
        for i in range(task_data["height"]):
            for j in range(task_data["width"]):
                box_id = task_data["boxes_table"][i][j]
                while box_id >= len(boxes):
                    boxes.append([])
                    boxes_borders.append({})
                boxes[box_id].append((i, j))
                
                for direction in directions:
                    ni, nj = i + direction[0], j + direction[1]
                    if 0 <= ni < task_data["height"] and 0 <= nj < task_data["width"]:
                        neighbor_box_id = task_data["boxes_table"][ni][nj]
                        if box_id != neighbor_box_id:
                            boxes_borders[box_id].setdefault(neighbor_box_id, [])
                            boxes_borders[box_id][neighbor_box_id].append((i, j, direction))
        
        task_data["boxes"] = boxes
        task_data["boxes_borders"] = boxes_borders
        return task_data

class BorderTaskParser(TaskParserBase):
    def parse(self, raw_task):
        """Parse border-based task into horizontal and vertical border constraints."""
        task_data = {}
        
        if '.' in raw_task:
            border = raw_task.split('/')
            border = [
                [int(y) if y.isdigit() else y for y in x.split('.')]
                for x in border
            ]
        else:
            border = [int(x) if x.isdigit() else x for x in raw_task.split('/')]
        
        if self.info.get("height") is not None:
            task_data["height"] = self.info.get("height")
        else:
            task_data["height"] = len(border) // 2
        task_data["width"] = len(border) - task_data["height"]
        task_data["vertical_borders"] = border[:task_data["width"]]  # up or down values
        task_data["horizontal_borders"] = border[task_data["width"]:]  # left or right values
        
        if "double_borders" in self.info:
            task_data["height"] //= 2
            task_data["width"] //= 2
        return task_data

class CellTableTaskParser(TaskParserBase):
    _DIRECTION_MAP = {
        'D': (1, 0),   # Down
        'U': (-1, 0),  # Up
        'R': (0, 1),   # Right
        'L': (0, -1),  # Left
    }

    def parse_number(self, s):
        """Extract leading digits from a string."""
        num = ""
        for char in s:
            if char.isdigit():
                num += char
            else:
                break
        return int(num) if num else None

    def parse_letters(self, s):
        """Parse direction letters into coordinate offsets."""
        letters = []
        for char in s:
            if char.isalpha() and char in self._DIRECTION_MAP:
                letters.append(self._DIRECTION_MAP[char])
        return letters

    def _parse_letters_binairo_plus(self, s):
        """Parse D=, Rx etc. from cell string (after optional digits). Returns list of ((dr, dc), 'same'|'opposite')."""
        result = []
        i = 0
        while i < len(s):
            if s[i] in self._DIRECTION_MAP and i + 1 < len(s) and s[i + 1] in ('=', 'x'):
                direction = self._DIRECTION_MAP[s[i]]
                constraint = 'same' if s[i + 1] == '=' else 'opposite'
                result.append((direction, constraint))
                i += 2
            else:
                i += 1
        return result
    
    def parse(self, raw_task):
        """Parse cell-based task with numbers and direction constraints.
        When info.binairo_plus is True, each cell may have constraint codes D=, Rx, etc. (same/opposite).
        """
        task_data = {}
        cells = raw_task.split(",")
        binairo_plus = self.info.get("binairo_plus", False)
        if binairo_plus:
            def constraint_part(cell):
                i = 0
                while i < len(cell) and cell[i].isdigit():
                    i += 1
                return cell[i:]
            cell_table = [self._parse_letters_binairo_plus(constraint_part(c)) for c in cells]
            n_cells = len(cell_table)
        else:
            table = list(map(self.parse_number, cells))
            cell_table = list(map(self.parse_letters, cells))
            n_cells = len(table)
        
        if self.info.get("height") is not None:
            task_data["height"] = self.info.get("height")
        else:
            task_data["height"] = int(sqrt(n_cells))
        task_data["width"] = n_cells // task_data["height"]
        if not binairo_plus:
            task_data["table"] = [
                table[i:i + task_data["width"]]
                for i in range(0, len(table), task_data["width"])
            ]
        task_data["cell_info_table"] = [
            cell_table[i:i + task_data["width"]]
            for i in range(0, len(cell_table), task_data["width"])
        ]
        return task_data


class WordsearchTaskParser(TaskParserBase):
    """Parse wordsearch task: grid of letters and list of words to find.
    Expected raw_task format: 'grid_part;word1,word2,...'
    Grid part: dense string of letters (height*width) or comma-separated letters.
    """

    def parse(self, raw_task):
        task_data = {}
        if ";" in raw_task:
            grid_part, words_part = raw_task.split(";", 1)
            words_str = words_part.strip()
            task_data["words"] = [w.strip().upper() for w in words_str.split(",") if w.strip()]
        else:
            grid_part = raw_task
            task_data["words"] = []

        # Build letter grid
        if "," in grid_part:
            letters = [c.strip().upper() for c in grid_part.split(",") if c.strip()]
        else:
            letters = [c.upper() for c in grid_part if c.isalpha()]

        height = self.info.get("height")
        width = self.info.get("width")
        if height is None:
            height = int(sqrt(len(letters)))
        if width is None:
            width = len(letters) // height if height else 0
        task_data["height"] = height
        task_data["width"] = width
        n = height * width
        letters = letters[:n]
        if len(letters) < n:
            letters.extend([" "] * (n - len(letters)))
        task_data["table"] = [
            [letters[i * width + j] for j in range(width)]
            for i in range(height)
        ]
        return task_data


class ShingokiTaskParser(TaskParserBase):
    """Parse Shingoki task: grid of dots with circle types and optional numbers.

    Expected raw_task format: 'types' or 'types;numbers'
    - types: comma-separated digits, 0=empty, 1=white circle, 2=black circle.
    - numbers: comma-separated digits 0-9; 0=no number, 1-9=sum of segment lengths.
    Grid is (height+1) x (width+1) dots; dimensions inferred from length (square grid).
    """

    def parse(self, raw_task):
        task_data = {}
        if ";" in raw_task:
            types_part, numbers_part = raw_task.split(";", 1)
            types_str = types_part.strip()
            numbers_str = numbers_part.strip()
        else:
            types_str = raw_task.strip()
            numbers_str = ""

        def parse_digit_list(s, default=0):
            out = []
            for x in s.split(","):
                x = x.strip()
                if not x:
                    continue
                if x.isdigit():
                    out.append(int(x))
                else:
                    out.append(default)
            return out

        types_list = parse_digit_list(types_str, default=0)
        numbers_list = parse_digit_list(numbers_str, default=0) if numbers_str else [0] * len(types_list)
        if len(numbers_list) < len(types_list):
            numbers_list.extend([0] * (len(types_list) - len(numbers_list)))
        numbers_list = numbers_list[: len(types_list)]

        n = len(types_list)
        if n == 0:
            task_data["height"] = 0
            task_data["width"] = 0
            task_data["table"] = []
            task_data["numbers_table"] = []
            return task_data

        size = int(sqrt(n))
        if size * size != n:
            size = max(1, int(sqrt(n)))
        width = n // size
        height = size if size * size == n else n // width

        if self.info.get("height") is not None:
            height = self.info["height"]
        if self.info.get("width") is not None:
            width = self.info["width"]

        task_data["height"] = height
        task_data["width"] = width
        task_data["table"] = [
            [types_list[i * width + j] for j in range(width)]
            for i in range(height)
        ]
        task_data["numbers_table"] = [
            [numbers_list[i * width + j] for j in range(width)]
            for i in range(height)
        ]
        return task_data


class ThermometersTaskParser(TaskParserBase):
    """Parse Thermometers task: row/column filled counts + thermometer paths.

    Expected raw_task format: 'border_part;paths_part'
    - border_part: same as BorderTaskParser: '/' separated numbers; first width values
      are column clues, next height values are row clues (filled cell counts).
    - paths_part: thermometers separated by '|'; each thermometer is comma-separated
      cell indices (row-major: index = r*width+c) from bulb to tip.
    """

    def parse(self, raw_task):
        task_data = {}
        if ";" in raw_task:
            border_part, paths_part = raw_task.split(";", 1)
        else:
            border_part = raw_task
            paths_part = ""

        # Parse border (row/column filled counts)
        if "." in border_part:
            border = border_part.split("/")
            border = [
                [int(y) if y.isdigit() else y for y in x.split(".")]
                for x in border
            ]
        else:
            border = [int(x) if x.isdigit() else x for x in border_part.split("/")]

        if self.info.get("height") is not None:
            task_data["height"] = self.info.get("height")
        else:
            task_data["height"] = len(border) // 2
        task_data["width"] = len(border) - task_data["height"]
        task_data["vertical_borders"] = border[: task_data["width"]]
        task_data["horizontal_borders"] = border[task_data["width"] :]

        height = task_data["height"]
        width = task_data["width"]
        n_cells = height * width

        # Parse thermometer paths: "i1,i2,i3|j1,j2|..."
        thermometers = []
        if paths_part.strip():
            for seg in paths_part.strip().split("|"):
                seg = seg.strip()
                if not seg:
                    continue
                path = []
                for s in seg.split(","):
                    s = s.strip()
                    if not s or not s.isdigit():
                        continue
                    idx = int(s)
                    if 0 <= idx < n_cells:
                        r, c = idx // width, idx % width
                        path.append((r, c))
                if path:
                    thermometers.append(path)
        task_data["thermometers"] = thermometers
        return task_data


class KakuroTaskParser(TaskParserBase):
    """Parse Kakuro task: grid of white/black cells plus down and across clues.

    Expected raw_task format: 'grid;down;across'
    - grid: same as TableTaskParser (0=white, 1=black; 0 may be stored as 2).
    - down: comma-separated numbers, one per cell (row-major), 0 = no down clue.
    - across: comma-separated numbers, one per cell (row-major), 0 = no across clue.
    """

    def parse(self, raw_task):
        task_data = {}
        parts = raw_task.split(";", 2)
        if len(parts) < 3:
            raise ValueError("Kakuro task must have three parts: grid;down;across")

        grid_part = parts[0].strip()
        down_part = parts[1].strip()
        across_part = parts[2].strip()

        # Parse grid: comma-separated (0/1 or W/B) or dense string
        table = []
        if "," in grid_part:
            for token in grid_part.split(","):
                token = token.strip()
                if token in ("W", "0"):
                    table.append(2)  # white, same as TableTaskParser
                elif token in ("B", "1"):
                    table.append(1)
                elif token.isdigit():
                    n = int(token)
                    table.append(2 if n == 0 else n)
                else:
                    table.append(2)
        else:
            char_idx = 0
            while char_idx < len(grid_part):
                char = grid_part[char_idx]
                if char in ("W", "B"):
                    table.append(0 if char == "W" else 1)
                elif char.isdigit():
                    char_start = char_idx
                    while char_idx + 1 < len(grid_part) and grid_part[char_idx + 1].isdigit():
                        char_idx += 1
                    number = int(grid_part[char_start : char_idx + 1])
                    table.append(2 if number == 0 else number)
                elif char == "_":
                    pass
                else:
                    table.extend([0] * (ord(char) - ord("a") + 1))
                char_idx += 1

        n_cells = len(table)
        if self.info.get("height") is not None:
            task_data["height"] = self.info["height"]
        else:
            task_data["height"] = int(sqrt(n_cells))
        task_data["width"] = n_cells // task_data["height"]
        task_data["table"] = [
            table[i : i + task_data["width"]]
            for i in range(0, len(table), task_data["width"])
        ]

        def parse_number_list(s):
            out = []
            for x in s.replace(",", " ").split():
                out.append(int(x) if x.isdigit() else 0)
            return out

        down_flat = parse_number_list(down_part)
        across_flat = parse_number_list(across_part)
        h, w = task_data["height"], task_data["width"]
        n = h * w
        while len(down_flat) < n:
            down_flat.append(0)
        while len(across_flat) < n:
            across_flat.append(0)
        task_data["down_clues"] = [
            down_flat[i : i + w] for i in range(0, n, w)
        ]
        task_data["across_clues"] = [
            across_flat[i : i + w] for i in range(0, n, w)
        ]
        return task_data


class CombinedTaskParser(TaskParserBase):
    def __init__(self, info={}, parsers=None, splitter=";"):
        TaskParserBase.__init__(self, info)
        self.parsers = parsers if parsers is not None else []
        self.splitter = splitter
    
    def parse(self, raw_task):
        raw_tasks = raw_task.split(self.splitter)
        combined_data = {}
        for task_index in range(len(raw_tasks)):
            parser = self.parsers[task_index](self.info)
            data = parser.parse(raw_tasks[task_index])
            for key in data:
                if key in combined_data:
                    suffix = 2
                    new_key = f"{key}_{suffix}"
                    while new_key in combined_data:
                        suffix += 1
                        new_key = f"{key}_{suffix}"
                    combined_data[new_key] = data[key]
                else:
                    combined_data[key] = data[key]
        return combined_data


