import argparse
import json
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from controller.chrome_controller import get_driver
from parser.parser import (
    extract_task,
    PuzzlePageError,
    TableTaskParser,
    BorderTaskParser,
    BoxesTaskParser,
    CellTableTaskParser,
    CombinedTaskParser,
    WordsearchTaskParser,
    ShingokiTaskParser,
    ThermometersTaskParser,
    KakuroTaskParser,
)
from solver import (
    sudoku_solver,
    kakurasu_solver,
    nonograms_solver,
    star_battle_solver,
    renzoku_solver,
    futoshiki_solver,
    skyscrapers_solver,
    killer_sudoku_solver,
    binairo_solver,
    binairo_plus_solver,
    norinori_solver,
    dominosa_solver,
    hitori_solver,
    kurodoko_solver,
    nurikabe_solver,
    stitches_solver,
    wordsearch_solver,
    boggle_solver,
    light_up_solver,
    shingoki_solver,
    battleships_solver,
    hashi_solver,
    heyawake_solver,
    masyu_solver,
    shikaku_solver,
    tents_solver,
    thermometers_solver,
    galaxies_solver,
    slither_link_solver,
    mosaic_solver,
    shakashaka_solver,
    pipes_solver,
    aquarium_solver,
    tapa_solver,
    yin_yang_solver,
    solo_chess_solver,
    chess_ranger_solver,
    chess_melee_solver,
)
from submitter.submitter import TableSubmitter, WordsearchSubmitter, WallsSubmitter, HashiSubmitter

# Constants
SUMMARY_FILE_PATH = "summary.json"
TIME_BUCKET_SIZE = 0.5
WAIT_SHORT = 0.1
WAIT_MEDIUM = 0.5
WAIT_LONG = 1.0

# Puzzle type constants
NUMERIC_PUZZLES = ["sudoku", "renzoku", "futoshiki", "jigsaw-sudoku", "skyscrapers", "killer-sudoku"]
REGULAR_SUBTABLE_PUZZLES = ["sudoku", "killer-sudoku"]
IRREGULAR_SUBTABLE_PUZZLES = ["star-battle", "jigsaw-sudoku"]
SUPPORTED_PUZZLES = ["sudoku", "kakurasu", "nonograms", "star-battle", "renzoku", 
                     "futoshiki", "jigsaw-sudoku", "skyscrapers", "killer-sudoku", "binairo", "binairo-plus", "norinori", "dominosa", "hitori", "kurodoko", "nurikabe", "stitches", "wordsearch", "boggle", "light-up", "shakashaka", "battleships", "hashi", "heyawake", "masyu", "shikaku", "tents", "lits", "thermometers", "galaxies", "slither-link", "minesweeper", "pipes", "aquarium", "tapa", "yin-yang", "solo-chess", "chess-ranger", "chess-melee"]
def main():
    """Main entry point for the puzzle solver."""
    parser = argparse.ArgumentParser(
        description="Solve puzzles from puzzles-mobile.com",
        epilog="Example: python main.py (ensure Chrome is open with a puzzle page loaded)"
    )
    parser.add_argument("--quest_mode", action="store_true", help="Enable quest mode.")
    parser.add_argument("--test_mode", action="store_true", help="Enable test mode.")
    parser.add_argument("--no_ignore_empty", action="store_true", help="Don't ignore empty cell markings (default: ignore empty cells).")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (progress updates and partial solution display).")
    parser.add_argument("--progress_interval", type=float, default=10.0, help="Interval in seconds for progress updates (default: 10.0).")
    parser.add_argument("--partial_interval", type=float, default=100.0, help="Interval in seconds for partial solution display (default: 100.0).")
    
    args = parser.parse_args()
    
    try:
        driver = get_driver()
    except Exception as e:
        print(f"\n❌ Error connecting to Chrome: {e}")
        print("\nPlease ensure:")
        print("  1. Chrome is running with remote debugging enabled:")
        print("     chrome.exe --remote-debugging-port=9222")
        print("  2. You have ChromeDriver installed or Chrome is accessible")
        raise SystemExit(1) from e
    
    try:
        debug_mode = args.debug  # Only show progress if debug mode is enabled
        ignore_empty = not args.no_ignore_empty  # Default is True (ignore empty)
        progress_interval = args.progress_interval
        partial_interval = args.partial_interval
        if args.quest_mode and not args.test_mode:
            run_quest_mode(driver, show_progress=debug_mode, ignore_empty=ignore_empty, 
                          progress_interval=progress_interval, partial_interval=partial_interval)
        else:
            run_solver(driver, test_mode=args.test_mode, ignore_empty=ignore_empty, 
                      show_progress=debug_mode, progress_interval=progress_interval, 
                      partial_interval=partial_interval)
    except (PuzzlePageError, SystemExit):
        # Already handled, just re-raise
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check that you're on a valid puzzle page and try again.")
        raise Exception(e) from e

def run_quest_mode(driver, show_progress=True, ignore_empty=True, progress_interval=10.0, partial_interval=100.0):
    """Run the solver in quest mode, continuously solving puzzles.
    
    Args:
        driver: Selenium WebDriver instance.
        show_progress: If True, show progress updates during solving.
        ignore_empty: If True, ignore empty cell markings for certain puzzles.
        progress_interval: Interval in seconds for progress updates (default: 10.0).
        partial_interval: Interval in seconds for partial solution display (default: 100.0).
    
    Raises:
        PuzzlePageError: If the current page is not a valid puzzle page.
        SystemExit: If a critical error occurs.
    """
    # Validate we're on a puzzle page before starting quest mode
    try:
        from parser.parser import validate_puzzle_page
        validate_puzzle_page(driver)
    except PuzzlePageError as e:
        print(f"\n❌ Error: {e}")
        print("\nQuest mode requires an active puzzle page.")
        print("Please navigate to a puzzle page first.")
        raise SystemExit(1) from e
    
    while True:
        try:
            run_solver(driver, test_mode=False, ignore_empty=ignore_empty, show_progress=show_progress,
                      progress_interval=progress_interval, partial_interval=partial_interval)
        except PuzzlePageError as e:
            print(f"\n❌ Error in quest mode: {e}")
            print("Quest mode stopped. Please navigate to a puzzle page and try again.")
            raise SystemExit(1) from e
        
        try:
            # Create a temporary submitter to use its methods
            from submitter.submitter import TableSubmitter
            temp_submitter = TableSubmitter(driver, {"height": 1, "width": 1}, offset=0)
            temp_submitter.open_new_puzzle(WAIT_SHORT, WAIT_MEDIUM, WAIT_LONG)
        except Exception as e:
            print(f"An error occurred in quest mode: {e}")
            print("Resetting puzzle and continuing...")
            try:
                # Create a temporary submitter to use its clear_grid method
                from submitter.submitter import TableSubmitter
                temp_submitter = TableSubmitter(driver, {"height": 1, "width": 1}, offset=0)
                temp_submitter.clear_grid()
            except Exception as reset_error:
                print(f"Failed to reset puzzle: {reset_error}")
                print("Quest mode stopped.")
                raise SystemExit(1) from reset_error


    
def summarize_task(info, time_diff):
    """Save task summary to JSON file with time statistics."""
    try:
        with open(SUMMARY_FILE_PATH, "r") as json_file:
            summary_data = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        summary_data = {}
    
    summary_data.setdefault(info["puzzle"], {})
    summary_data[info["puzzle"]].setdefault(info["type"], {})
    
    bucket_index = int(time_diff // TIME_BUCKET_SIZE)
    time_range = f"{bucket_index * TIME_BUCKET_SIZE}-{(bucket_index + 1) * TIME_BUCKET_SIZE}"
    
    summary_data[info["puzzle"]][info["type"]].setdefault(time_range, 0)
    summary_data[info["puzzle"]][info["type"]][time_range] += 1
    
    with open(SUMMARY_FILE_PATH, "w") as json_file:
        json.dump(summary_data, json_file, indent=4)

def configure_puzzle_info(info):
    """Configure puzzle-specific metadata based on puzzle type.
    
    Args:
        info: Dictionary containing puzzle information.
    
    Raises:
        PuzzlePageError: If the puzzle type is not supported.
    """
    puzzle_type = info.get("puzzle", "")
    
    # Validate puzzle type is supported
    if puzzle_type not in SUPPORTED_PUZZLES:
        raise PuzzlePageError(
            f"Unsupported puzzle type: '{puzzle_type}'\n"
            f"Supported types: {', '.join(SUPPORTED_PUZZLES)}\n"
            "Please navigate to a supported puzzle page."
        )
    
    # Set puzzle type
    info["puzzle_type"] = "numeric" if puzzle_type in NUMERIC_PUZZLES else ""
    
    # Set subtable type
    if puzzle_type in REGULAR_SUBTABLE_PUZZLES:
        info["subtable_type"] = "regular"
    elif puzzle_type in IRREGULAR_SUBTABLE_PUZZLES:
        info["subtable_type"] = "irregular"
    else:
        info["subtable_type"] = "no_tables"
    
    # Special case for killer-sudoku
    if puzzle_type == "killer-sudoku" and info.get("type") in ["weekly", "monthly"]:
        info["subtable_type"] = "irregular"
    
    # Special case for skyscrapers
    if puzzle_type == "skyscrapers":
        info["double_borders"] = True

    # Binairo, Binairo+, and Battleships use a binary table: 0 and 1 are treated as W/B by the parser
    if puzzle_type in ("binairo", "binairo-plus", "battleships", "yin-yang"):
        info["binary"] = True
    if puzzle_type == "binairo-plus":
        info["binairo_plus"] = True


def create_parser(info):
    """Create the appropriate parser for the puzzle type."""
    parser_map = {
        "sudoku": lambda: TableTaskParser(info),
        "kakurasu": lambda: BorderTaskParser(info),
        "nonograms": lambda: BorderTaskParser(info),
        "star-battle": lambda: BoxesTaskParser(info),
        "renzoku": lambda: CellTableTaskParser(info),
        "futoshiki": lambda: CellTableTaskParser(info),
        "jigsaw-sudoku": lambda: CombinedTaskParser(info, [TableTaskParser, BoxesTaskParser]),
        "skyscrapers": lambda: CombinedTaskParser(info, [BorderTaskParser, TableTaskParser], ","),
        "killer-sudoku": lambda: _create_killer_sudoku_parser(info),
        "binairo": lambda: TableTaskParser(info),
        "binairo-plus": lambda: CombinedTaskParser(info, [TableTaskParser, CellTableTaskParser], "|"),
        "norinori": lambda: BoxesTaskParser(info),
        "hitori": lambda: TableTaskParser(info),
        "hashi": lambda: TableTaskParser(info),
        "kurodoko": lambda: TableTaskParser(info),
        "nurikabe": lambda: TableTaskParser(info),
        "stitches": lambda: CombinedTaskParser(info, [BorderTaskParser, BoxesTaskParser], ";"),
        "wordsearch": lambda: WordsearchTaskParser(info),
        "boggle": lambda: WordsearchTaskParser(info),
        "shingoki": lambda: ShingokiTaskParser(info),
        "masyu": lambda: ShingokiTaskParser(info),
        "kakuro": lambda: KakuroTaskParser(info),
        "slither-link": lambda: TableTaskParser(info),
        "slant": lambda: TableTaskParser(info),
        "battleships": lambda: CombinedTaskParser(info, [BorderTaskParser, TableTaskParser], ","),
        "shikaku": lambda: TableTaskParser(info),
        "tents": lambda: CombinedTaskParser(info, [BorderTaskParser, TableTaskParser], ","),
        "galaxies": lambda: ShingokiTaskParser(info),
        "minesweeper": lambda: TableTaskParser(info),
        "shakashaka": lambda: TableTaskParser(info),
        "pipes": lambda: TableTaskParser(info),
        "aquarium": lambda: CombinedTaskParser(info, [BorderTaskParser, BoxesTaskParser], ";"),
        "tapa": lambda: TableTaskParser(info),
        "solo-chess": lambda: TableTaskParser(info),
        "chess-ranger": lambda: TableTaskParser(info),
        "chess-melee": lambda: TableTaskParser(info),
    }
    
    puzzle_type = info["puzzle"]
    if puzzle_type not in parser_map:
        raise NotImplementedError(f"Parser for puzzle type '{puzzle_type}' is not implemented.")
    
    return parser_map[puzzle_type]()


def _create_killer_sudoku_parser(info):
    """Create parser for killer-sudoku based on subtable type."""
    if info["subtable_type"] == "regular":
        return CombinedTaskParser(info, [TableTaskParser, BoxesTaskParser, TableTaskParser])
    else:  # irregular
        return CombinedTaskParser(info, [TableTaskParser, BoxesTaskParser, BoxesTaskParser, TableTaskParser])


def apply_puzzle_specific_config(info):
    """Apply puzzle-specific configuration after parsing."""
    # Nonograms special case
    if info["puzzle"] == "nonograms" and info["type"] == "daily":
        info["height"] = 30

    # Sudoku and killer-sudoku subtable dimensions
    if info["puzzle"] in ["sudoku", "killer-sudoku"]:
        if info["height"] == 16:
            info["subtable_height"] = 4
        elif info["height"] in [4, 6]:
            info["subtable_height"] = 2
        else:
            info["subtable_height"] = 3
        info["subtable_width"] = info["height"] // info["subtable_height"]
    
    # Star-battle items per box
    if info["puzzle"] == "star-battle":
        info["items_per_box"] = (
            1 + (info["height"] >= 10) + (info["height"] >= 14) + 
            (info["height"] >= 17) + (info["height"] >= 21) + (info["height"] >= 25)
        )
    
    # Killer-sudoku special flag
    if info["puzzle"] == "killer-sudoku":
        info["killer_x"] = info["type"] in ["daily", "monthly"]

    # Stitches: stitches per adjacent block pair (2÷ → 2, 3÷ → 3, etc.)
    if info["puzzle"] == "stitches":
        puzzle_type_str = str(info.get("type", "1"))
        if puzzle_type_str.isdigit():
            info["stitches_per_pair"] = int(puzzle_type_str)
        else:
            info["stitches_per_pair"] = 1

    # Slant: parsed table is (H+1)x(W+1) point clues; set height/width to cell grid
    if info["puzzle"] == "slant" and "table" in info and info["table"]:
        info["height"] = len(info["table"]) - 1
        info["width"] = len(info["table"][0]) - 1


def create_solver(info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
    """Create the appropriate solver for the puzzle type.
    
    Args:
        info: Dictionary containing puzzle information.
        show_progress: If True, show progress updates during solving.
        partial_solution_callback: Optional callback to display partial solution.
        progress_interval: Interval in seconds for progress updates (default: 10.0).
        partial_interval: Interval in seconds for partial solution display (default: 100.0).
    
    Returns:
        Solver instance for the puzzle type.
    """
    solvers = {
        "sudoku": sudoku_solver.SudokuSolver,
        "kakurasu": kakurasu_solver.KakurasuSolver,
        "nonograms": nonograms_solver.NonogramsSolver,
        "star-battle": star_battle_solver.StarBattleSolver,
        "renzoku": renzoku_solver.RenzokuSolver,
        "futoshiki": futoshiki_solver.FutoshikiSolver,
        "jigsaw-sudoku": sudoku_solver.SudokuSolver,
        "skyscrapers": skyscrapers_solver.SkyscrapersSolver,
        "killer-sudoku": killer_sudoku_solver.KillerSudokuSolver,
        "binairo": binairo_solver.BinairoSolver,
        "binairo-plus": binairo_plus_solver.BinairoPlusSolver,
        "norinori": norinori_solver.NorinoriSolver,
        "dominosa": dominosa_solver.DominosaSolver,
        "hitori": hitori_solver.HitoriSolver,
        "kurodoko": kurodoko_solver.KurodokoSolver,
        "nurikabe": nurikabe_solver.NurikabeSolver,
        "stitches": stitches_solver.StitchesSolver,
        "wordsearch": wordsearch_solver.WordsearchSolver,
        "boggle": boggle_solver.BoggleSolver,
        "light-up": light_up_solver.LightUpSolver,
        "battleships": battleships_solver.BattleshipsSolver,
        "heyawake": heyawake_solver.HeyawakeSolver,
        "masyu": masyu_solver.MasyuSolver,
        "shikaku": shikaku_solver.ShikakuSolver,
        "tents": tents_solver.TentsSolver,
        "lits": lits_solver.LitsSolver,
        "thermometers": thermometers_solver.ThermometersSolver,
        "galaxies": galaxies_solver.GalaxiesSolver,
        "slither-link": slither_link_solver.SlitherLinkSolver,
        "kakuro": kakuro_solver.KakuroSolver,
        "shakashaka": shakashaka_solver.ShakashakaSolver,
        "pipes": pipes_solver.PipesSolver,
        "aquarium": aquarium_solver.AquariumSolver,
        "slant": slant_solver.SlantSolver,
        "tapa": tapa_solver.TapaSolver,
        "yin-yang": yin_yang_solver.YinYangSolver,
        "solo-chess": solo_chess_solver.SoloChessSolver,
        "chess-ranger": chess_ranger_solver.ChessRangerSolver,
        "chess-melee": chess_melee_solver.ChessMeleeSolver,
    }
    
    puzzle_type = info["puzzle"]
    if puzzle_type not in solvers:
        raise NotImplementedError(f"Solver for puzzle type '{puzzle_type}' is not implemented.")
    
    return solvers[puzzle_type](info, show_progress=show_progress, partial_solution_callback=partial_solution_callback,
                                progress_interval=progress_interval, partial_interval=partial_interval)


def calculate_submission_offset(info):
    """Calculate the offset for puzzle submission based on puzzle type."""
    if info["puzzle"] == "nonograms":
        horizontal_sum = sum(len(v) for v in info["horizontal_borders"])
        vertical_sum = sum(len(v) for v in info["vertical_borders"])
        return horizontal_sum + vertical_sum
    return 0


def create_submitter(driver, info, offset=0):
    """Create the appropriate submitter for the puzzle type."""
    if info["puzzle"] in ("wordsearch", "boggle"):
        return WordsearchSubmitter(driver, info, offset=offset)
    if info["puzzle"] == "slither-link":
        submit_info = {**info, "height": info["height"] + 1, "width": info["width"] + 1}
        return WallsSubmitter(driver, submit_info, offset=offset)
    if info["puzzle"] in ("shingoki", "masyu", "galaxies"):
        return WallsSubmitter(driver, info, offset=offset)
    if info["puzzle"] == "hashi":
        return HashiSubmitter(driver, info, offset=offset)
    return TableSubmitter(driver, info, offset=offset)


def apply_ignore_empty_filter(info, ignore_empty):
    """Apply ignore_empty filter to solution if needed."""
    if not ignore_empty:
        return
    
    if info["puzzle"] in ["nonograms", "kakurasu"]:
        for i in range(info["height"]):
            for j in range(info["width"]):
                if info["solution"][i][j] == 2:
                    info["solution"][i][j] = 0
    elif info["puzzle"] == "star-battle":
        for i in range(info["height"]):
            for j in range(info["width"]):
                if info["solution"][i][j] == 1:
                    info["solution"][i][j] = 0


def run_solver(driver, test_mode=False, ignore_empty=True, show_progress=True, progress_interval=10.0, partial_interval=100.0):
    """Main solver workflow: extract, parse, solve, and submit puzzle.
    
    Args:
        driver: Selenium WebDriver instance.
        test_mode: If True, don't save statistics.
        ignore_empty: If True, ignore empty cell markings for certain puzzles (default: True).
        show_progress: If True, show progress updates during solving.
        progress_interval: Interval in seconds for progress updates (default: 10.0).
        partial_interval: Interval in seconds for partial solution display (default: 100.0).
    
    Raises:
        PuzzlePageError: If the current page is not a valid puzzle page.
        SystemExit: If a critical error occurs.
    """
    print("Starting puzzle solver...")
    
    try:
        # Step 1: Extract the task from the webpage
        info = extract_task(driver)
        print(f"Detected puzzle: {info}")
    except PuzzlePageError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease ensure:")
        print("  1. You're on puzzles-mobile.com")
        print("  2. You've navigated to a specific puzzle page")
        print("  3. The puzzle has fully loaded")
        print("  4. You're not on the homepage or a non-puzzle page")
        raise SystemExit(1) from e
    
    # Step 2: Configure puzzle metadata
    configure_puzzle_info(info)
    
    # Step 3: Parse the task
    parser = create_parser(info)
    parsed_task = parser.parse(info["task"])
    print(f"Parsed task data: {parsed_task}")
    info.update(parsed_task)
    
    # Step 4: Apply puzzle-specific configuration
    apply_puzzle_specific_config(info)
    
    # Step 5: Initialize solver
    print(f"Initializing {info['puzzle']} solver...")
    init_start_time = time.time()
    
    # Create submitter early for partial solution display
    offset = calculate_submission_offset(info)
    submitter = create_submitter(driver, info, offset=offset)
    
    # Create callback for partial solution display
    def display_partial_solution(board):
        """Callback to display partial solution every 100 seconds."""
        try:
            print("Clearing grid and displaying partial solution...")
            submitter.clear_grid()
            time.sleep(0.5)  # Wait for grid to clear
            submitter.submit(board)
            print("Partial solution displayed.")
        except Exception as e:
            print(f"Warning: Could not display partial solution: {e}")
    
    solver = create_solver(
        info, 
        show_progress=show_progress,
        partial_solution_callback=display_partial_solution if show_progress else None,
        progress_interval=progress_interval,
        partial_interval=partial_interval
    )
    init_end_time = time.time()
    init_time_diff = init_end_time - init_start_time
    print(f"Solver initialized in {init_time_diff:.2f} seconds.")
    
    # Step 6: Solve puzzle
    if show_progress:
        print("Solving puzzle (debug mode: progress updates every 10 seconds, partial solution every 100 seconds)...")
    else:
        print("Solving puzzle...")
    solve_start_time = time.time()
    if show_progress and hasattr(solver, '_start_progress_tracking'):
        solver._start_progress_tracking()
    try:
        info["solution"] = solver.solve()
    finally:
        if show_progress and hasattr(solver, '_stop_progress_tracking'):
            solver._stop_progress_tracking()
    solve_end_time = time.time()
    solve_time_diff = solve_end_time - solve_start_time
    print(f"Solved puzzle in {solve_time_diff:.2f} seconds.")
    
    total_time = init_time_diff + solve_time_diff
    print(f"Total time: {total_time:.2f} seconds (init: {init_time_diff:.2f}s, solve: {solve_time_diff:.2f}s)")
    
    if not test_mode:
        # Use solving time (not initialization time) for statistics
        summarize_task(info, solve_time_diff)
    
    # Step 7: Submit solution
    if info["puzzle"] not in SUPPORTED_PUZZLES:
        raise NotImplementedError(f"Submitter for puzzle type '{info['puzzle']}' is not implemented.")
    
    apply_ignore_empty_filter(info, ignore_empty)
    
    # Submitter already created, clear grid then submit the final solution
    print("Clearing grid before submission...")
    submitter.clear_grid()
    time.sleep(0.5)  # Wait for grid to clear
    print("Submitting solution...")
    submitter.submit(info["solution"])

if __name__ == "__main__":
    main()