# TFT Finder

A tool to optimize your team composition in **Teamfight Tactics** (Season 16).
Select your champions, and the tool recommends the best next unit to buy based on trait synergies, unit tier, and drop probabilities.

![Screenshot](data/images/screenshot/app1.png)

---

## Requirements

- **Python 3** installed on your PC ([download here](https://www.python.org/downloads/))
  - During installation, **make sure to check "Add Python to PATH"**
- **Pillow** (an image display library)

## Installation

1. **Download the project** (green "Code" button > "Download ZIP" on GitHub, then unzip)

2. **Open a terminal** in the project folder
   - On Windows: right-click in the folder > "Open in Terminal"

3. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```
   > **pip not recognized?** pip is installed automatically with Python. If the command doesn't work:
   > - Make sure you checked **"Add Python to PATH"** during Python installation (otherwise, relaunch the Python installer > "Modify" > check the box)
   > - Try `python -m pip install -r requirements.txt` instead

## Running

In the terminal, type:

```
python app.py
```

The application opens — you're ready!

## How it works

1. **Click on champions** to add them to your team
2. Use the **search bar** to filter by name, cost, or trait
3. **Sort the grid** by default, cost, or tier using the sort buttons
4. Check the **active traits** on the right (colored bronze/white/gold/prismatic based on the tier reached)
5. The tool suggests the **best champions** to complete your team
   - Traits in **green** are already in your team (direct synergy)
   - The score breakdown (tier + traits) is shown under each recommendation
   - Recommended champions are **highlighted in orange** in the grid
6. Click a **recommendation** to add it directly
7. Adjust the **team size** to see drop probabilities
8. **Config**: open the config panel to adjust scoring weights (tier, synergies, odds, multi-synergy) or use a **preset** (Balanced, Max synergy, Brute force, Ignore odds)

### Keyboard shortcuts

- **Ctrl+Z**: undo last action
- **Escape**: deselect all

## License

This project is licensed under the **MIT License** — you are free to use, modify, and redistribute it as you wish. See the [LICENSE](LICENSE) file for details.
