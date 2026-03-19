from selenium import webdriver


def get_driver():
    """Create and return a Chrome WebDriver instance connected to an existing Chrome session.
    
    This function connects to a Chrome instance running with remote debugging enabled
    on localhost:9222. The browser window will be maximized.
    
    Returns:
        webdriver.Chrome: A Chrome WebDriver instance.
    """
    options = webdriver.ChromeOptions()
    options.debugger_address = "localhost:9222"
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    for handle in driver.window_handles:
      driver.switch_to.window(handle)
      if "puzzles-mobile.com" in driver.current_url:
        break
    return driver
