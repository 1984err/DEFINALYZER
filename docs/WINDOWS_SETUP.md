# Windows Setup and Troubleshooting

Run commands from the DEFINALYZER project folder.

## PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
crawl4ai-setup
python main.py
```

If PowerShell blocks `Activate.ps1`, either run the virtual environment without
activation:

```powershell
.\.venv\Scripts\python.exe main.py
```

or allow locally created scripts for only the current PowerShell process:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

The process-scoped policy ends when that PowerShell window closes.

## Command Prompt

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
crawl4ai-setup
python main.py
```

`source` is a macOS/Linux shell command. It is not used in Windows Command
Prompt.

## Running without activation

Activation is only a convenience that places the virtual environment first on
the command path. Every command can instead call its Python executable
directly:

```powershell
.\.venv\Scripts\python.exe main.py --help
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Virtual environment returns Access denied

A virtual environment is disposable; it contains installed packages, not
DEFINALYZER research. Preserve `.env` and `output/`.

1. Close terminals or programs that may still be using `.venv`.
2. Rename `.venv` to `.venv-old` as a recoverable backup.
3. Create `.venv` again and reinstall `requirements.txt`.
4. Run the test suite before deleting `.venv-old`.

Never copy a virtual environment between computers or move it with the
project. Recreate it instead.

## Hermes checks

Hermes is installed separately from DEFINALYZER. First confirm its own command
works:

```powershell
hermes --version
hermes doctor
```

Then test the integration:

```powershell
python main.py provider test
```

Provider **status** only confirms that a configured executable can be found.
Provider **test** starts a real, minimal model request and confirms that the
provider, model, and authentication all work together.

If Hermes reports missing configuration, run `hermes setup`. If `hermes.exe`
itself reports a missing Python module, repair or reinstall Hermes with its
official installer/updater; changing the DEFINALYZER virtual environment will
not repair the separate Hermes installation.

DEFINALYZER stores no Hermes credentials. Authentication remains managed by
Hermes.

## Browser setup

If crawling fails because a browser executable is missing, rerun:

```powershell
crawl4ai-setup
```

This browser download is not needed for project management, saved-output
status, CoinGecko refreshes, or the standalone blockchain collector.
