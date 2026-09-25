"""Local PyInstaller hook for the repository workflow package.

The project contains a local package named workflow. The PyInstaller
community hook with the same module name assumes that a separately installed
PyPI distribution named workflow exists, which is not true here.

Keep this hook intentionally empty: the application local workflow package
is discovered normally by module analysis.
"""
