from selenium.webdriver.common.by import By
from time import sleep
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException


def human_delay():
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
    def __init__(self, driver, info={},offset=0):
        self.driver = driver
        self.info = info
        self.extract(offset)

    def extract(self,offset=0):
        self.all_cells = self.driver.find_elements(By.CSS_SELECTOR, ".selectable")
        
    def submit(self, solution):
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    def submit_val(self, cell, value):
        puzzle_type = self.info.get("puzzle_type", "")
        if puzzle_type == "":
            for _ in range(value):
                smart_click(self.driver, cell)
        elif puzzle_type == "numeric":
            smart_write_number(self.driver, cell, value)
    
class TableSubmitter(SubmitterBase):
    def extract(self,offset=0):
        super().extract(offset)
        self.cells=[]
        for cellx in range(self.info["height"]):
            cells_row = []
            for celly in range(self.info["width"]):
                index=cellx*self.info["width"]+celly + offset
                cells_row.append(self.all_cells[index])
            self.cells.append(cells_row)

    
    def submit(self, solution):
        for row in range(self.info["height"]):
            for col in range(self.info["width"]):
                cell = self.cells[row][col]
                value = solution[row][col]
                if value == 0:
                    continue  # Skip empty cells
                self.submit_val(cell, value)
                
class WallsSubmitter(SubmitterBase):
    def extract(self,offset=0):
        super().extract(offset)
        self.horizontal_walls = []
        self.vertical_walls = []
        for wallx in range(self.info["height"]):
            hwalls_row = []
            for wally in range(self.info["width"] - 1):
                index = wallx * (self.info["width"] - 1) + wally + offset
                hwalls_row.append(self.all_cells[index])
            self.horizontal_walls.append(hwalls_row)
        offset = self.info["height"] * (self.info["width"] - 1)
        for wallx in range(self.info["height"] - 1):
            vwalls_row = []
            for wally in range(self.info["width"]):
                index = offset + wallx * self.info["width"] + wally + offset
                vwalls_row.append(self.all_cells[index])
            self.vertical_walls.append(vwalls_row)
    
    def submit(self, solution):
        for row in range(self.info["height"]):
            for col in range(self.info["width"] - 1):
                cell = self.horizontal_walls[row][col]
                value = solution["horizontal_walls"][row][col]
                if value == 0:
                    continue  # Skip no-wall cells
                self.submit_val(cell, value)
        for row in range(self.info["height"] - 1):
            for col in range(self.info["width"]):
                cell = self.vertical_walls[row][col]
                value = solution["vertical_walls"][row][col]
                if value == 0:
                    continue  # Skip no-wall cells
                self.submit_val(cell, value)

class WallsAndTablesSubmitter(TableSubmitter, WallsSubmitter):
    def extract(self):
        TableSubmitter.extract(self,0)
        offset = self.info["height"] * self.info["width"]
        WallsSubmitter.extract(self,offset)

    def submit(self, solution):
        TableSubmitter.submit(self, solution["table"])
        WallsSubmitter.submit(self, solution)