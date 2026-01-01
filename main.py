from controller.chrome_controller import get_driver
from parser.parser import *
from solver import *
from submitter.submitter import *
from solver import *
import argparse, time, json
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
test_mode = False
ignore_empty = False
def main():
    parser = argparse.ArgumentParser(description="Solve a puzzle.")
    parser.add_argument("--quest_mode", action="store_true", help="Enable quest mode.")
    parser.add_argument("--test_mode", action="store_true", help="Enable test mode.")
    parser.add_argument("--ignore_empty", action="store_true", help="Ignore x values.")
    
    args = parser.parse_args()
    global test_mode
    test_mode = args.test_mode
    global ignore_empty
    ignore_empty = args.ignore_empty
    driver = get_driver()
    if args.quest_mode and not test_mode:
        while True:
            run_solver(driver)
            try:
                time.sleep(0.5)
                check_puzzle_solved(driver)
                time.sleep(0.5)
                new_puzzle = []
                while new_puzzle == []:
                    new_puzzle = driver.find_elements(By.CSS_SELECTOR, ".new-puzzle")
                    time.sleep(0.1)  # Wait until the new puzzle button appears
                new_puzzle[0].click()
                time.sleep(1)  # Wait before checking for the next puzzle
            except Exception as e:
                print("An error occurred in quest mode:", e)
                print("Resetting puzzle and continuing...")
                reset_puzzle(driver)

    else:
        run_solver(driver)

def check_puzzle_solved(driver):
    if driver.find_elements(By.CSS_SELECTOR, ".new-puzzle") != []:
        return  # Puzzle already solved
    if driver.find_elements(By.CSS_SELECTOR, "puzzle-button[caption='Check']") == []:
        smart_click(driver,driver.find_elements(By.ID, "additional-menu")[0])
        time.sleep(0.5)  # Wait before checking for the next puzzle
    smart_click(driver,driver.find_elements(By.CSS_SELECTOR, "puzzle-button[caption='Check']")[0])
    time.sleep(0.5)  # Wait before checking for the next puzzle
    smart_click(driver,driver.find_elements(By.ID, "additional-menu")[0])
    
def summarize_task(info, time_diff):
    # Save to summary file
    json_file_path = "summary.json"
    summary_data = json.loads(open(json_file_path, "r").read())
    summary_data.setdefault(info["puzzle"], {})
    summary_data[info["puzzle"]].setdefault(info["type"], {})
    time_range = f"{int(time_diff // 0.5) * 0.5}-{(int(time_diff // 0.5) + 1) * 0.5}"
    summary_data[info["puzzle"]][info["type"]].setdefault(time_range, 0)
    summary_data[info["puzzle"]][info["type"]][time_range] += 1
    with open(json_file_path, "w") as json_file:
        json.dump(summary_data, json_file, indent=4)

def reset_puzzle(driver):
    if driver.find_elements(By.CSS_SELECTOR, "puzzle-button[caption='Restart']") == []:
        smart_click(driver,driver.find_elements(By.ID, "additional-menu")[0])
        time.sleep(0.5)  # Wait before checking for the next puzzle
    smart_click(driver,driver.find_elements(By.CSS_SELECTOR, "puzzle-button[caption='Restart']")[0])
    time.sleep(0.5)  # Wait before checking for the next puzzle
    actions = ActionChains(driver)
    actions.send_keys(Keys.ENTER).perform()
    time.sleep(0.5)  # Wait before checking for the next puzzle
    smart_click(driver,driver.find_elements(By.ID, "additional-menu")[0])
    
def run_solver(driver):   
    print("Starting puzzle solver...")
    # Step 1: Extract the task from the webpage
    info = extract_task(driver)

    print("Detected puzzle:", info)
    if info["puzzle"] in ["sudoku", "renzoku", "futoshiki", "jigsaw-sudoku", "skyscrapers", "killer-sudoku"]:
        info["puzzle_type"] = "numeric"
    else:
        info["puzzle_type"] = ""

    if info["puzzle"] in ["sudoku", "killer-sudoku"]:
        info["subtable_type"] = "regular" #squares
    elif info["puzzle"] in ["star-battle","jigsaw-sudoku"]:
        info["subtable_type"] = "irregular" #squares
    else:
        info["subtable_type"] = "no_tables"

    if info["puzzle"]=="killer-sudoku" and info["type"] in ["weekly","monthly"]:
        info["subtable_type"] = "irregular"
    if info["puzzle"] in ["skyscrapers"]:
        info["double_borders"] = True

    # Step 2: Parse the task
    if info["puzzle"] in ["sudoku"]:
        parser = TableTaskParser(info)
    elif info["puzzle"] in ["kakurasu", "nonograms"]:
        parser = BorderTaskParser(info)
    elif info["puzzle"] in ["star-battle"]:
        parser = BoxesTaskParser(info)
    elif info["puzzle"] in ["renzoku","futoshiki"]:
        parser = CellTableTaskParser(info)
    elif info["puzzle"] in ["jigsaw-sudoku"]:
        parser = CombinedTaskParser(info,[TableTaskParser,BoxesTaskParser])
    elif info["puzzle"] in ["skyscrapers"]:
        parser = CombinedTaskParser(info,[BorderTaskParser,TableTaskParser],",")
    elif info["puzzle"] in ["killer-sudoku"]:
        if info["subtable_type"] == "regular":
            parser = CombinedTaskParser(info, [TableTaskParser,BoxesTaskParser,TableTaskParser])
        elif info["subtable_type"] == "irregular":
            parser = CombinedTaskParser(info, [TableTaskParser,BoxesTaskParser,BoxesTaskParser,TableTaskParser])
    else:
        raise NotImplementedError(f"Parser for puzzle type '{info['puzzle']}' is not implemented.")
    
    if info["puzzle"] == "nonograms":
        if info["type"] == "daily":
            info["height"] = 30
        
    parsed_task = parser.parse(info["task"])
    print("Parsed task data:", parsed_task)
    info.update(parsed_task)

    if info["puzzle"] in ["sudoku", "killer-sudoku"]:
        if info["height"]==16:
            info["subtable_height"] = 4
        elif info["height"] in [4,6]:
            info["subtable_height"] = 2
        else:
            info["subtable_height"] = 3
        info["subtable_width"] = info["height"] // info["subtable_height"]
    
    if info["puzzle"] in ["star-battle"]:
        info["items_per_box"]=1 + (info["height"] >=10) + (info["height"] >=14) + (info["height"] >=17) +\
                                        (info["height"] >=21) + (info["height"] >=25)
    
    if info["puzzle"]=="killer-sudoku" :
        info["killer_x"] = info["type"] in ["daily","monthly"]
    # Step 3: Solve puzzle
    solvers = {
        "sudoku":sudoku_solver.SudokuSolver,
        "kakurasu":kakurasu_solver.KakurasuSolver,
        "nonograms":nonograms_solver.NonogramsSolver,
        "star-battle":star_battle_solver.StarBattleSolver,
        "renzoku":renzoku_solver.RenzokuSolver,
        "futoshiki":futoshiki_solver.FutoshikiSolver,
        "jigsaw-sudoku":sudoku_solver.SudokuSolver,
        "skyscrapers":skyscrapers_solver.SkyscrapersSolver,
        "killer-sudoku":killer_sudoku_solver.KillerSudokuSolver
    }
    start_time = time.time()
    if info["puzzle"] in solvers:
        solver = solvers[info["puzzle"]](info)
    else:
        raise NotImplementedError(f"Solver for puzzle type '{info['puzzle']}' is not implemented.")
    end_time = time.time()
    time_diff = end_time - start_time
    print(f"Initiated puzzle solver in {time_diff:.2f} seconds.")
    #timing start

    start_time = time.time()
    info["solution"] = solver.solve()
    end_time = time.time()
    time_diff = end_time - start_time
    print(f"Solved puzzle in {time_diff:.2f} seconds.")
    if not test_mode:
        summarize_task(info, time_diff)
    
    # # Step 4: Submit like human
    offset = 0
    if info["puzzle"] == "nonograms":
        offset = sum(map(lambda v:len(v), info["horizontal_borders"])) + sum(map(lambda v:len(v), info["vertical_borders"]))

        
    if info["puzzle"] in ["sudoku", "kakurasu","nonograms","star-battle","renzoku", "futoshiki", "jigsaw-sudoku", "skyscrapers", "killer-sudoku"]:
        submitter = TableSubmitter(driver, info,offset=offset)
    else:
        raise NotImplementedError(f"Submitter for puzzle type '{info['puzzle']}' is not implemented.")

    if ignore_empty:
        if info["puzzle"] in ["nonograms","kakurasu"]:
            for i in range(info["height"]):
                for j in range(info["width"]):
                    if info["solution"][i][j] == 2:
                        info["solution"][i][j] = 0
        elif info["puzzle"] in ["star-battle"]:
            for i in range(info["height"]):
                for j in range(info["width"]):
                    if info["solution"][i][j] == 1:
                        info["solution"][i][j] = 0
    submitter.submit(info["solution"])

if __name__ == "__main__":
    main()