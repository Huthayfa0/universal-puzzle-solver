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
    
    Reads the puzzle task from the browser's JavaScript Settings.bag object,
    puzzle dimensions from Game.puzzleHeight / Game.puzzleWidth, and puzzle type
    from the current URL.
    
    Args:
        driver: Selenium WebDriver instance pointing to the puzzle page.
    
    Returns:
        dict: Dictionary containing:
            - "puzzle": Puzzle type (e.g., "sudoku", "kakurasu")
            - "type": Puzzle difficulty/variant (e.g., "daily", "weekly")
            - "task": Raw task string to be parsed
            - "height": Puzzle height from Game.puzzleHeight (if available)
            - "width": Puzzle width from Game.puzzleWidth (if available)
            - "single_option": Present if the save entry in Settings.bag includes it
              (enables :class:`TableTaskParser` compact ``bb_ca__``-style encoding)
    
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
    
    # Extract puzzle dimensions from Game object
    try:
        height = driver.execute_script("return typeof Game !== 'undefined' ? Game.puzzleHeight : null;")
        width = driver.execute_script("return typeof Game !== 'undefined' ? Game.puzzleWidth : null;")
        if height is not None and width is not None:
            try:
                info["height"] = int(height)
                info["width"] = int(width)
            except (TypeError, ValueError):
                pass  # Parsers will derive from task
    except Exception:
        pass  # Parsers will derive height/width from task if not set
    
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
        When info['single_number'] is True, each cell is a single digit (one number per cell);
        only one digit is consumed per token and 0/1 are stored as 'W'/'B'. Otherwise, multi-digit
        numbers are allowed and 0 is stored as 2; letter expansion uses 2 or 0 accordingly.

        When info['single_option'] is True, the task is a run-length form for a binary-ish grid where
        each cell is either empty (0) or filled (1). Lowercase letters expand to *n* zeros followed by
        one 1, with n = 1 for 'a', 2 for 'b', etc. (e.g. ``a`` → ``[0, 1]``, ``b`` → ``[0, 0, 1]``).
        Underscore ``_`` is a single 1. Example: ``"bb_ca__"`` →
        ``[0,0,1,0,0,1,1,0,0,0,1,0,1,1,1]``. Uppercase and digit rules are unchanged.
        """
        task_data = {}
        table = []
        char_idx = 0
        single_number = self.info.get("single_number", False)
        single_option = self.info.get("single_option", False)

        while char_idx < len(raw_task):
            char = raw_task[char_idx]
            if char.isupper():
                table.append(char)
            elif char.isdigit():
                char_start = char_idx
                while (not single_number and char_idx + 1 < len(raw_task)) and raw_task[char_idx + 1].isdigit():
                    char_idx += 1
                number = int(raw_task[char_start:char_idx + 1])
                table.append('Zero' if number == 0 else number)
            elif char == '_':
                if single_option:
                    table.append(1)
                else:
                    pass  # Skip underscore (non single_option)
            elif char.islower():
                n = ord(char) - ord('a') + 1
                # n zeros
                table.extend([0] * n)
                if single_option:
                    table.append(1)
            char_idx += 1
        
        task_data["height"] = self.info.get("height")
        task_data["width"] = self.info.get("width")
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
        
        task_data["height"] = self.info.get("height")
        task_data["width"] = self.info.get("width")
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
        
        # Consider '.' or '_' as possible splitters (both for joining and for split)
        if '.' in raw_task or '_' in raw_task or ',' in raw_task:
            border = raw_task.split('/')
            # For each border, split by '.', '_', or ',' and parse as int if digit
            def smart_split(x):
                if '.' in x:
                    cells = x.split('.')
                elif '_' in x:
                    cells = x.split('_')
                elif ',' in x:
                    cells = x.split(',')
                else:
                    cells = [x]
                return [int(y) if y.isdigit() else y for y in cells]
            border = [y for x in border for y in smart_split(x)]
        else:
            border = [int(x) if x.isdigit() else x for x in raw_task.split('/')]
        
        task_data["height"] = self.info.get("height")
        task_data["width"] = self.info.get("width")
        if "double_borders" in self.info:
            task_data["vertical_borders"] = border[:task_data["width"] * 2]
            task_data["horizontal_borders"] = border[task_data["width"] * 2:]
        else:
            task_data["vertical_borders"] = border[:task_data["width"]]  # up or down values
            task_data["horizontal_borders"] = border[task_data["width"]:]  # left or right values
        
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
        
        task_data["height"] = self.info.get("height")
        task_data["width"] = self.info.get("width")
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

        task_data["height"] = self.info.get("height")
        task_data["width"] = self.info.get("width")
        height = task_data["height"]
        width = task_data["width"]
        n = height * width
        letters = letters[:n]
        if len(letters) < n:
            letters.extend([" "] * (n - len(letters)))
        task_data["table"] = [
            [letters[i * width + j] for j in range(width)]
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

        task_data["height"] = self.info.get("height")
        task_data["width"] = self.info.get("width")
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


class CombinedTaskParser(TaskParserBase):
    def __init__(self, info={}, parsers=None, splitter=";"):
        TaskParserBase.__init__(self, info)
        self.parsers = parsers if parsers is not None else []
        self.splitter = splitter
    
    def parse(self, raw_task):
        raw_tasks = raw_task.split(self.splitter)
        combined_data = {}
        for task_index in range(len(self.parsers)):
            parser = self.parsers[task_index](self.info)
            data = parser.parse(raw_tasks[task_index] if task_index != len(self.parsers)-1 else self.splitter.join(raw_tasks[task_index:]))
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


class DominosaTableTaskParser(TaskParserBase):
    def parse(self, raw_task):
        """Parse table-based task into a 2D grid structure.
        When info['single_number'] is True, each cell is a single digit (one number per cell);
        only one digit is consumed per token and 0/1 are stored as 'W'/'B'. Otherwise, multi-digit
        numbers are allowed and 0 is stored as 2; letter expansion uses 2 or 0 accordingly.
        """
        task_data = {}
        table = []
        char_idx = 0

        while char_idx < len(raw_task):
            char = raw_task[char_idx]
            if char.isdigit():
                number = int(char)
                table.append(number)
            elif char == '[':
                char_end = char_idx + 1
                while raw_task[char_end] != ']':
                    char_end += 1
                number = int(raw_task[char_idx + 1:char_end])
                table.append(number)
                char_idx = char_end
            char_idx += 1
        
        task_data["height"] = self.info.get("height")+1
        task_data["width"] = self.info.get("width")+2
        task_data["table"] = [
            table[i:i + task_data["width"]]
            for i in range(0, len(table), task_data["width"])
        ]
        return task_data