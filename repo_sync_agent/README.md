# Repository Sync Agent

Temporary local development utility.

GitHub is the source of truth. The local Product Workbench checkout is used for running and testing.

Every 60 seconds the agent checks for uncommitted local changes, fetches origin/main, and synchronizes only when the working tree is clean.

After pulling these files, move the repo_sync_agent folder outside the repository if you want to keep this utility separate.
