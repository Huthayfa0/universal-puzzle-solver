import random
import time
from time import sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoAlertPresentException,
)


def human_delay():
    """Add a random human-like delay between actions."""
    sleep(random.uniform(0.05, 0.15))

# -----------------------------------------------------------------------------
# Use browser's existing getBoundingClientRect() to compute the real x,y
# -----------------------------------------------------------------------------
def get_element_center(driver, element):
    return driver.execute_script("""
        const r = arguments[0].getBoundingClientRect();
        return {x: r.left + r.width / 2, y: r.top + r.height / 2};
    """, element)


# -----------------------------------------------------------------------------
# Selenium fallback click: Uses built-in element.click() and ActionChains
# -----------------------------------------------------------------------------
def selenium_try_click(driver, element):
    try:
        # Try standard Selenium click first
        element.click()
        return True
    except (ElementClickInterceptedException, ElementNotInteractableException):
        pass

    try:
        # Try moving and clicking via ActionChains (still Selenium-native)
        actions = ActionChains(driver)
        actions.move_to_element(element).click().perform()
        return True
    except Exception:
        return False


# -----------------------------------------------------------------------------
# Perform an accurate pixel-click (JS event at exact x,y)
# -----------------------------------------------------------------------------
def perform_js_coordinate_click(driver, x, y):
    driver.execute_script("""
        const x = arguments[0];
        const y = arguments[1];

        // Using the browser's built-ins: elementFromPoint() truly replicates human click targeting
        const elem = document.elementFromPoint(x, y);
        if (!elem) return;

        ['mousedown', 'mouseup', 'click'].forEach(type => {
            elem.dispatchEvent(new MouseEvent(type, {
                bubbles: true,
                cancelable: true,
                clientX: x,
                clientY: y
            }));
        });
    """, x, y)


# -----------------------------------------------------------------------------
# click by element, using all built-in Selenium methods first
# -----------------------------------------------------------------------------
def smart_click(driver, element):
    # Try Selenium built-in behavior first
    if selenium_try_click(driver, element):
        return True

    # If Selenium failed, compute real transformed x,y
    x, y = get_element_center(driver, element)

    # Then perform a true browser-level click as a fallback
    perform_js_coordinate_click(driver, x, y)
    return True

def smart_write(driver, element, text):
    smart_click(driver, element)
    actions = ActionChains(driver)
    for char in str(text):
        actions.send_keys(char).perform()

def smart_write_number(driver, element, number):
    smart_write(driver, element, number if number <= 9 else chr(number - 10 + ord('a')))

class SubmitterBase:
    def __init__(self, driver, info=None, offset=0):
        self.driver = driver
        self.info = info if info is not None else {}
        self.offset = offset  # Store offset for re-extraction after clear_grid
        self.extract(offset)

    def extract(self, offset=0):
        """Extract all selectable cells from the page."""
        self.all_cells = self.driver.find_elements(By.CSS_SELECTOR, ".selectable")
    
    def clear_grid(self):
        """Clear the grid by using the restart functionality.
        
        Note: After clearing, cell elements become stale and need to be re-extracted.
        Call extract() after clear_grid() if you plan to use the cells afterward.
        """
        # Try to find restart button
        restart_button = self.driver.find_elements(By.CSS_SELECTOR, "puzzle-button[caption='Restart']")
        if not restart_button:
            # Open menu if restart button is not visible
            menu = self.driver.find_elements(By.ID, "additional-menu")
            if menu:
                smart_click(self.driver, menu[0])
                time.sleep(0.5)
        
        # Click restart button
        restart_button = self.driver.find_elements(By.CSS_SELECTOR, "puzzle-button[caption='Restart']")
        if restart_button:
            smart_click(self.driver, restart_button[0])
            time.sleep(0.5)
        
        # Handle the alert dialog if it appears
        try:
            alert = self.driver.switch_to.alert
            alert.accept()  # Accept the "Start over?" confirmation
            time.sleep(0.5)
        except NoAlertPresentException:
            # No alert appeared, try pressing ENTER as fallback
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.ENTER).perform()
            time.sleep(0.5)
        
        # Close menu if it's open
        menu = self.driver.find_elements(By.ID, "additional-menu")
        if menu:
            smart_click(self.driver, menu[0])
            time.sleep(0.5)
        
        # Wait a bit for the page to stabilize after restart
        time.sleep(0.5)
        
        # Re-extract cells after restart (they become stale)
        self.extract(self.offset)
    
    def check_puzzle_solved(self):
        """Check if puzzle is solved and click the check button if needed."""
        if self.driver.find_elements(By.CSS_SELECTOR, ".new-puzzle"):
            return  # Puzzle already solved
        
        check_button = self.driver.find_elements(By.CSS_SELECTOR, "puzzle-button[caption='Check']")
        if not check_button:
            menu = self.driver.find_elements(By.ID, "additional-menu")
            if menu:
                smart_click(self.driver, menu[0])
                time.sleep(0.5)
        
        check_button = self.driver.find_elements(By.CSS_SELECTOR, "puzzle-button[caption='Check']")
        if check_button:
            smart_click(self.driver, check_button[0])
            time.sleep(0.5)
        
        menu = self.driver.find_elements(By.ID, "additional-menu")
        if menu:
            smart_click(self.driver, menu[0])
    
    def open_new_puzzle(self, wait_short=0.1, wait_medium=0.5, wait_long=1.0):
        """Open a new puzzle after the current one is solved.
        
        Args:
            wait_short: Short delay in seconds (default: 0.1).
            wait_medium: Medium delay in seconds (default: 0.5).
            wait_long: Long delay in seconds (default: 1.0).
        """
        time.sleep(wait_medium)
        self.check_puzzle_solved()
        time.sleep(wait_medium)
        
        new_puzzle = []
        while new_puzzle == []:
            new_puzzle = self.driver.find_elements(By.CSS_SELECTOR, ".new-puzzle")
            time.sleep(wait_short)
        
        new_puzzle[0].click()
        time.sleep(wait_long)
        
    def submit(self, solution):
        """Submit the solution to the puzzle. Must be overridden by subclasses."""
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    def submit_val(self, cell, value):
        """Submit a single value to a cell based on puzzle type."""
        puzzle_type = self.info.get("puzzle_type", "")
        if puzzle_type == "":
            # For non-numeric puzzles, click the cell multiple times
            for _ in range(value):
                smart_click(self.driver, cell)
        elif puzzle_type == "numeric":
            # For numeric puzzles, write the number directly
            smart_write_number(self.driver, cell, value)
    
class TableSubmitter(SubmitterBase):
    def extract(self, offset=0):
        """Extract table cells and organize them into a 2D grid."""
        super().extract(offset)
        self.cells = []
        for row in range(self.info["height"]):
            cells_row = []
            for col in range(self.info["width"]):
                index = row * self.info["width"] + col + offset
                cells_row.append(self.all_cells[index])
            self.cells.append(cells_row)

    def submit(self, solution):
        """Submit the solution by filling in all non-zero values."""
        for row in range(self.info["height"]):
            for col in range(self.info["width"]):
                cell = self.cells[row][col]
                value = solution[row][col]
                if value == 0:
                    continue  # Skip empty cells
                self.submit_val(cell, value)
                
class WallsSubmitter(SubmitterBase):
    def extract(self, offset=0):
        """Extract horizontal and vertical wall cells."""
        super().extract(offset)
        self.horizontal_walls = []
        self.vertical_walls = []
        
        # Extract horizontal walls
        for row in range(self.info["height"]):
            hwalls_row = []
            for col in range(self.info["width"] - 1):
                index = row * (self.info["width"] - 1) + col + offset
                hwalls_row.append(self.all_cells[index])
            self.horizontal_walls.append(hwalls_row)
        
        # Extract vertical walls
        vertical_offset = self.info["height"] * (self.info["width"] - 1) + offset
        for row in range(self.info["height"] - 1):
            vwalls_row = []
            for col in range(self.info["width"]):
                index = vertical_offset + row * self.info["width"] + col
                vwalls_row.append(self.all_cells[index])
            self.vertical_walls.append(vwalls_row)
    
    def submit(self, solution):
        """Submit horizontal and vertical wall solutions."""
        # Submit horizontal walls
        for row in range(self.info["height"]):
            for col in range(self.info["width"] - 1):
                cell = self.horizontal_walls[row][col]
                value = solution["horizontal_walls"][row][col]
                if value == 0:
                    continue  # Skip no-wall cells
                self.submit_val(cell, value)
        
        # Submit vertical walls
        for row in range(self.info["height"] - 1):
            for col in range(self.info["width"]):
                cell = self.vertical_walls[row][col]
                value = solution["vertical_walls"][row][col]
                if value == 0:
                    continue  # Skip no-wall cells
                self.submit_val(cell, value)

class WallsAndTablesSubmitter(TableSubmitter, WallsSubmitter):
    def extract(self, offset=0):
        """Extract both table cells and wall cells."""
        TableSubmitter.extract(self, 0)
        walls_offset = self.info["height"] * self.info["width"]
        WallsSubmitter.extract(self, walls_offset)

    def submit(self, solution):
        """Submit both table and wall solutions."""
        TableSubmitter.submit(self, solution["table"])
        WallsSubmitter.submit(self, solution)