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
    return webdriver.Chrome(options=options)
