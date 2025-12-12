from selenium import webdriver

def get_driver():
 
    options = webdriver.ChromeOptions()
    options.debugger_address = "localhost:9222"
    options.add_argument("--start-maximized")
    return webdriver.Chrome(options=options)
