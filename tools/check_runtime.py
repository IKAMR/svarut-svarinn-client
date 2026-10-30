"""Offline installation check. Does not read any user configuration."""
import sys


def main() -> int:
    if sys.version_info < (3, 11):
        print("Python 3.11 or newer is required.")
        return 1
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        version = root.tk.call("info", "patchlevel")
        root.destroy()
    except Exception:
        print("Tcl/Tk could not start. Install Python with Tcl/Tk and use a desktop session.")
        return 1
    try:
        import cryptography
    except ImportError:
        print("cryptography is missing. Run install.bat again.")
        return 1
    print(f"cryptography {cryptography.__version__}: OK")
    print(f"Python {sys.version.split()[0]} and Tcl/Tk {version}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
