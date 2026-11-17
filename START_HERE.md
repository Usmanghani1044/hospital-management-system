# Start here — Muhammad Usman Ghani

## Open the project

1. Double-click the ZIP to extract it.
2. In VS Code choose **File → Open Folder**.
3. Choose **hospital-management**, the folder containing `main.py`.
4. Choose **Terminal → New Terminal**.
5. Type this command and press Enter:

```bash
python3 main.py
```

Your dashboard opens in your browser. Keep the VS Code terminal running while you use it.

**You do not need to run pip install or create a virtual environment.**

On Windows the command is `py main.py`.

## If the browser does not open

Copy this into your browser's address bar:

http://127.0.0.1:8765

Do not double-click `index.html`: the dashboard needs the Python server.

## If the port is already in use

```bash
python3 main.py --port 8766
```

Then open http://127.0.0.1:8766.

## Stop and start later

Press **Control+C** in the terminal to stop. Next time, open the same folder and run `python3 main.py` again. Your saved changes remain in `runtime/hospital.sqlite3`.

## Make a fresh demonstration without losing your work

Stop the running server, then run:

```bash
python3 main.py --db runtime/fresh-demo.sqlite3
```

A new file gets new fictional sample data. Reusing an existing path reopens that database.

## Back up your data

Go to **Reports & activity → Download database backup**. Keep the downloaded file somewhere safe. To open that backup, stop the server and use `--db` with its file path; put paths with spaces inside quotation marks.

## If Python is missing

Install Python from the official python.org website, reopen VS Code and retry. This app needs Python 3.9+ and SQLite 3.31+ (normally bundled with Python). It uses fictional patient records only.
