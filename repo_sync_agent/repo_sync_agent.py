import subprocess
import time
from datetime import datetime
from pathlib import Path

REPO_PATH = Path(r"C:\01 Projects\mk_product_workbench")
BRANCH = "main"
CHECK_INTERVAL = 60

def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"[{timestamp}] {message}"
    print(text)
    with (Path(__file__).parent / "sync.log").open("a", encoding="utf-8") as file:
        file.write(text + "\n")

def run_git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO_PATH, capture_output=True, text=True)

def working_tree_clean() -> bool:
    result = run_git("status", "--porcelain")
    return result.returncode == 0 and not result.stdout.strip()

def get_commit(ref: str) -> str | None:
    result = run_git("rev-parse", ref)
    return result.stdout.strip() if result.returncode == 0 else None

def sync_repository() -> None:
    if not REPO_PATH.exists():
        log(f"ERROR: Repository not found: {REPO_PATH}")
        return
    if not working_tree_clean():
        log("WARNING: Local changes detected. Sync skipped to protect local work.")
        return
    fetch = run_git("fetch", "origin")
    if fetch.returncode != 0:
        log(f"ERROR: Git fetch failed: {fetch.stderr.strip()}")
        return
    local_commit = get_commit("HEAD")
    remote_commit = get_commit(f"origin/{BRANCH}")
    if not local_commit or not remote_commit:
        log("ERROR: Could not determine repository commits.")
        return
    if local_commit == remote_commit:
        return
    log(f"New GitHub commit detected: {remote_commit[:8]}")
    reset = run_git("reset", "--hard", f"origin/{BRANCH}")
    if reset.returncode != 0:
        log(f"ERROR: Sync failed: {reset.stderr.strip()}")
        return
    log(f"Repository synchronized to {remote_commit[:8]}")

def main() -> None:
    log("Repository Sync Agent started.")
    log(f"Repository: {REPO_PATH}")
    log(f"Branch: {BRANCH}")
    log(f"Check interval: {CHECK_INTERVAL} seconds")
    while True:
        try:
            sync_repository()
        except Exception as error:
            log(f"ERROR: Unexpected error: {error}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
