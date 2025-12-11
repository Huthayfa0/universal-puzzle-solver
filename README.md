# 🧩 Universal Puzzle Solver (puzzles-mobile.com)

A modular Python framework that automatically detects, parses, solves, and fills puzzle solutions directly on **puzzles-mobile.com**.

This project uses browser automation to read the puzzle state from the active page, converts the HTML into structured puzzle data, and runs the appropriate solver based on the puzzle type.

---

## 🚀 Features

- Detects the puzzle from the active Chrome tab  
- Parses the puzzle grid from the HTML `<div id="game">` container  
- Identifies the puzzle type automatically  
- Solves puzzles using dedicated solver modules  
- Fills the solution back into the webpage using Selenium/Playwright  
