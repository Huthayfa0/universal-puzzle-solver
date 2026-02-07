# 🧩 Universal Puzzle Solver (puzzles-mobile.com)

A modular Python framework that automatically detects, parses, solves, and fills puzzle solutions directly on **puzzles-mobile.com**.

This project uses browser automation to read the puzzle state from the active page, converts the HTML into structured puzzle data, and runs the appropriate solver based on the puzzle type.

---

## 🚀 Features

- **Automatic Puzzle Detection**: Detects puzzle type from the active Chrome tab
- **Smart Parsing**: Converts HTML puzzle data into structured formats
- **Advanced Solvers**: Dedicated solver modules with constraint propagation
- **Browser Integration**: Fills solutions back into the webpage using Selenium
- **Quest Mode**: Continuously solve puzzles in a loop
- **Performance Tracking**: Records solve times in `summary.json`

---

## 📦 Supported Puzzles

The solver supports the following puzzle types:

- **Sudoku** - Classic 9x9 and variants (4x4, 6x6, 16x16)
- **Jigsaw Sudoku** - Sudoku with irregular regions
- **Killer Sudoku** - Sudoku with cage sum constraints (with optional X variant)
- **Kakurasu** - Fill cells to match row and column sums
- **Nonograms** - Picture logic puzzles with row/column clues
- **Star Battle** - Place stars with adjacency and region constraints
- **Renzoku** - Sudoku with adjacent number constraints
- **Futoshiki** - Sudoku with inequality constraints
- **Skyscrapers** - Sudoku with visibility constraints

---

## 🛠️ Installation

### Prerequisites

- Python 3.7+
- Chrome browser
- ChromeDriver (or Chrome with remote debugging enabled)

### Setup

1. Install dependencies:
```bash
pip install selenium
```

2. Start Chrome with remote debugging:
```bash
chrome.exe --remote-debugging-port=9222
```

3. Navigate to a puzzle on puzzles-mobile.com in the Chrome window

---

## 📖 Usage

### Basic Usage

```bash
python main.py
```

This will:
1. Connect to the active Chrome tab
2. Detect and parse the puzzle
3. Solve it using the appropriate solver
4. Fill the solution back into the webpage

### Command Line Options

```bash
# Quest mode - continuously solve puzzles
python main.py --quest_mode

# Test mode - solve without saving statistics
python main.py --test_mode

# Don't ignore empty values - mark empty cells for certain puzzles
python main.py --no_ignore_empty

# Debug mode - show progress updates and partial solution display
python main.py --debug

# Debug mode with custom intervals (progress every 5s, partial every 50s)
python main.py --debug --progress_interval 5.0 --partial_interval 50.0

# Combine options
python main.py --quest_mode --debug
python main.py --quest_mode --debug --progress_interval 2.0 --partial_interval 30.0
```

### Options

- `--quest_mode`: Enable quest mode to continuously solve puzzles
- `--test_mode`: Enable test mode (doesn't save statistics)
- `--no_ignore_empty`: Don't ignore empty cell markings (default: empty cells are ignored for nonograms, kakurasu, star-battle)
- `--debug`: Enable debug mode with progress updates and partial solution display
  - Progress updates are printed every 10 seconds (default)
  - Partial solutions are displayed every 100 seconds (default)
- `--progress_interval SECONDS`: Set the interval for progress updates in seconds (default: 10.0)
- `--partial_interval SECONDS`: Set the interval for partial solution display in seconds (default: 100.0)

**Note**: Progress tracking and partial solution display are only enabled when `--debug` is specified. Without debug mode, the solver runs silently for maximum performance.

---

## 🏗️ Project Structure

```
universal-puzzle-solver/
├── main.py                 # Main entry point
├── controller/             # Browser automation
│   └── chrome_controller.py
├── parser/                 # Puzzle parsing
│   └── parser.py
├── solver/                 # Puzzle solvers
│   ├── sudoku_solver.py
│   ├── kakurasu_solver.py
│   ├── nonograms_solver.py
│   ├── star_battle_solver.py
│   ├── renzoku_solver.py
│   ├── futoshiki_solver.py
│   ├── skyscrapers_solver.py
│   └── killer_sudoku_solver.py
└── submitter/             # Solution submission
    └── submitter.py
```

---

## 🔧 How It Works

1. **Extraction**: Reads puzzle data from the webpage's JavaScript state
2. **Parsing**: Converts raw puzzle strings into structured data structures
3. **Configuration**: Sets up puzzle-specific metadata and constraints
4. **Solving**: Uses constraint propagation and backtracking algorithms
5. **Submission**: Fills the solution back into the webpage cells

---

## 📊 Performance Tracking

The solver automatically tracks solve times in `summary.json`:
- Organizes by puzzle type and difficulty
- Groups solve times into buckets (e.g., 0.0-0.5 seconds)
- Useful for analyzing solver performance

---

## 🧪 Solver Algorithms

Each solver uses specialized techniques:

- **Sudoku variants**: Constraint propagation, naked/hidden subsets, pointing pairs
- **Nonograms**: Line-by-line constraint propagation with backtracking
- **Kakurasu**: Common value deduction across all possible line configurations
- **Star Battle**: Feasibility checking with adjacency constraints
- **Skyscrapers**: Pre-computed state spaces with visibility constraints

---

## 📝 License

See [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
