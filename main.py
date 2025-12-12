from controller.chrome_controller import get_driver
from parser.parser import *
from submitter.submitter import *
from solver.solver import *
import argparse, time, json

def main():
    parser = argparse.ArgumentParser(description="Solve a puzzle.")
    parser.add_argument("--quest_mode", action="store_true", help="Enable quest mode.")
    
    args = parser.parse_args()
    driver = get_driver()
    if args.quest_mode:
        while True:
            run_solver(driver)
            time.sleep(0.5)
            check_puzzle_solved(driver)
            time.sleep(0.5)
            new_puzzle = []
            while new_puzzle == []:
                new_puzzle = driver.find_elements(By.CSS_SELECTOR, ".new-puzzle")
                time.sleep(0.1)  # Wait until the new puzzle button appears
            new_puzzle[0].click()
            time.sleep(1)  # Wait before checking for the next puzzle

    else:
        run_solver(driver)

def check_puzzle_solved(driver):
    if driver.find_elements(By.CSS_SELECTOR, ".new-puzzle") != []:
        return  # Puzzle already solved
    if driver.find_elements(By.CSS_SELECTOR, "puzzle-button[caption='Check']") == []:
        driver.find_elements(By.ID, "additional-menu")[0].click()
        time.sleep(0.5)  # Wait before checking for the next puzzle
    driver.find_elements(By.CSS_SELECTOR, "puzzle-button[caption='Check']")[0].click()
    time.sleep(0.5)  # Wait before checking for the next puzzle
    driver.find_elements(By.ID, "additional-menu")[0].click()


def run_solver(driver):   
    # read json summary file
    print("Starting puzzle solver...")
    # this file is to summarize all solved puzzles speeds
    json_file_path = "summary.json"
    summary_data = json.loads(open(json_file_path, "r").read())

    # Step 1: Extract the task from the webpage
    info = extract_task(driver)

    print("Detected puzzle:", info["puzzle"], "of type:", info["type"])
    if info["puzzle"] == "sudoku":
        info["puzzle_type"] = "numeric"
    else:
        info["puzzle_type"] = ""
    # Step 2: Parse the task
    if info["puzzle"] == "sudoku":
        parser = TableTaskParser(info)
    else:
        raise NotImplementedError(f"Parser for puzzle type '{info['puzzle']}' is not implemented.")
    parsed_task = parser.parse(info["task"])
    print("Parsed task data:", parsed_task)
    info.update(parsed_task)
    # Step 3: Solve puzzle
    if info["puzzle"] == "sudoku":
        solver = SudokuSolver(info)
    else:
        raise NotImplementedError(f"Solver for puzzle type '{info['puzzle']}' is not implemented.")
    #timing start

    start_time = time.time()
    info["solution"] = solver.solve()
    end_time = time.time()
    print(f"Solved puzzle in {end_time - start_time:.2f} seconds.")
    # Save to summary file
    summary_data.setdefault(info["puzzle"], {})
    summary_data[info["puzzle"]].setdefault(info["type"], {})
    summary_data[info["puzzle"]][info["type"]].setdefault(f"{end_time - start_time:.1f}", 0)
    summary_data[info["puzzle"]][info["type"]][f"{end_time - start_time:.1f}"] += 1
    with open(json_file_path, "w") as json_file:
        json.dump(summary_data, json_file, indent=4)
    # # Step 4: Submit like human
    if info["puzzle"] == "sudoku":
        submitter = TableSubmitter(driver, info)
    else:
        raise NotImplementedError(f"Submitter for puzzle type '{info['puzzle']}' is not implemented.")

    submitter.submit(info["solution"])

if __name__ == "__main__":
    main()