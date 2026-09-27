#!/usr/bin/env python3
"""
Masoud Windows Bridge 1.0.0

Repository-backed local worker for controlled Windows development tasks.

Security boundaries:
- File access only inside configured allowed_roots.
- Remote process execution only for an explicit executable allow-list.
- No shell=True, no cmd.exe, and no remote PowerShell.
- write/delete/mkdir/run require a local ARMED switch.
- Only bridge/inbox and bridge/outbox are ever staged by this worker.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import traceback
from pathlib import Path
from typing import Any

BRIDGE_VERSION = "1.0.0"
DEFAULT_BRANCH = "windows-bridge"
MAX_READ_BYTES = 1_000_000
MAX_WRITE_BYTES = 1_500_000
MAX_OUTPUT_CHARS = 120_000
MAX_LIST_ITEMS = 2_000


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def normalize_path(p: str) -> str:
    return os.path.normcase(os.path.abspath(os.path.expandvars(os.path.expanduser(p))))


def is_within(path: Path, roots: list[Path]) -> bool:
    candidate = normalize_path(str(path))
    for root in roots:
        root_n = normalize_path(str(root))
        try:
            if os.path.commonpath([candidate, root_n]) == root_n:
                return True
        except ValueError:
            continue
    return False


def safe_path(raw: str, roots: list[Path]) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("path must be a non-empty string")
    p = Path(os.path.expandvars(os.path.expanduser(raw))).resolve(strict=False)
    if not is_within(p, roots):
        raise PermissionError(f"path is outside allowed_roots: {p}")
    return p


def load_config(repo_root: Path) -> dict[str, Any]:
    default_local = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MasoudWindowsBridge" / "config.json"
    config_path = Path(os.environ.get("MASOUD_BRIDGE_CONFIG", str(default_local)))

    cfg: dict[str, Any] = {
        "branch": DEFAULT_BRANCH,
        "poll_seconds": 5,
        "repo_path": str(repo_root),
        "bridge_repo_path": str(repo_root),
        "allowed_roots": [r"C:\AI_System", str(repo_root)],
        "allowed_executables": [
            "git", "git.exe",
            "python", "python.exe", "py", "py.exe",
            "node", "node.exe",
            "npm", "npm.cmd", "npm.exe",
            "npx", "npx.cmd", "npx.exe",
            "bun", "bun.exe", "bunx", "bunx.exe",
            "adb", "adb.exe",
            "gradle", "gradle.bat", "gradle.exe",
        ],
        "armed_file": str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MasoudWindowsBridge" / "ARMED"),
        "max_run_seconds": 300,
    }

    if config_path.exists():
        with config_path.open("r", encoding="utf-8-sig") as f:
            user_cfg = json.load(f)
        if not isinstance(user_cfg, dict):
            raise ValueError("config.json must contain a JSON object")
        cfg.update(user_cfg)

    cfg["repo_path"] = str(Path(cfg["repo_path"]).resolve())
    cfg["bridge_repo_path"] = str(Path(cfg.get("bridge_repo_path", repo_root)).resolve())
    cfg["allowed_roots"] = [str(Path(p).resolve()) for p in cfg["allowed_roots"]]
    bridge_root = str(Path(cfg["bridge_repo_path"]).resolve())
    if bridge_root not in cfg["allowed_roots"]:
        cfg["allowed_roots"].append(bridge_root)
    cfg["armed_file"] = str(Path(cfg["armed_file"]).resolve())
    cfg["branch"] = str(cfg.get("branch") or DEFAULT_BRANCH)
    cfg["poll_seconds"] = max(2, int(cfg.get("poll_seconds", 5)))
    cfg["max_run_seconds"] = min(300, max(1, int(cfg.get("max_run_seconds", 300))))
    return cfg


def run_git(repo: Path, args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        text=True,
        capture_output=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )


def current_branch(repo: Path) -> str:
    r = run_git(repo, ["branch", "--show-current"])
    if r.returncode != 0:
        raise RuntimeError(f"git branch check failed: {r.stderr.strip()}")
    return r.stdout.strip()


def git_sync(repo: Path, branch: str) -> None:
    r = run_git(repo, ["pull", "--ff-only", "origin", branch], timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"git pull failed: {r.stderr.strip() or r.stdout.strip()}")


def armed(cfg: dict[str, Any]) -> bool:
    p = Path(cfg["armed_file"])
    return p.exists() and p.read_text(encoding="utf-8", errors="ignore").strip().upper() == "ARMED"


def require_armed(cfg: dict[str, Any]) -> None:
    if not armed(cfg):
        raise PermissionError("bridge is disarmed; local ARMED switch is missing")


def output_limit(s: str) -> str:
    return s if len(s) <= MAX_OUTPUT_CHARS else s[:MAX_OUTPUT_CHARS] + "\n...[truncated]..."


def op_read_file(command: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    p = safe_path(command["path"], [Path(x) for x in cfg["allowed_roots"]])
    if not p.is_file():
        raise FileNotFoundError(str(p))
    size = p.stat().st_size
    if size > MAX_READ_BYTES:
        raise ValueError(f"file too large: {size} bytes")
    return {"path": str(p), "bytes": size, "content": p.read_text(encoding="utf-8", errors="replace")}


def op_list_dir(command: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    p = safe_path(command["path"], [Path(x) for x in cfg["allowed_roots"]])
    if not p.is_dir():
        raise NotADirectoryError(str(p))
    include_hidden = bool(command.get("include_hidden", False))
    items: list[dict[str, Any]] = []
    for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if len(items) >= MAX_LIST_ITEMS:
            break
        if not include_hidden and child.name.startswith("."):
            continue
        try:
            items.append({
                "name": child.name,
                "path": str(child),
                "type": "dir" if child.is_dir() else "file",
                "bytes": child.stat().st_size if child.is_file() else None,
            })
        except OSError:
            items.append({"name": child.name, "path": str(child), "type": "unknown"})
    return {"path": str(p), "items": items}


def op_write_file(command: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    require_armed(cfg)
    p = safe_path(command["path"], [Path(x) for x in cfg["allowed_roots"]])
    content = command.get("content")
    if not isinstance(content, str):
        raise ValueError("content must be a string")
    data = content.encode("utf-8")
    if len(data) > MAX_WRITE_BYTES:
        raise ValueError(f"content too large: {len(data)} bytes")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return {"path": str(p), "bytes_written": len(data)}


def op_delete_file(command: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    require_armed(cfg)
    p = safe_path(command["path"], [Path(x) for x in cfg["allowed_roots"]])
    if not p.exists():
        return {"path": str(p), "deleted": False, "reason": "not_found"}
    if p.is_dir():
        raise IsADirectoryError("delete_file cannot delete directories")
    p.unlink()
    return {"path": str(p), "deleted": True}


def op_mkdir(command: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    require_armed(cfg)
    p = safe_path(command["path"], [Path(x) for x in cfg["allowed_roots"]])
    p.mkdir(parents=True, exist_ok=True)
    return {"path": str(p), "created": True}


def op_run(command: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    require_armed(cfg)
    exe = command.get("executable")
    args = command.get("args", [])
    cwd_raw = command.get("cwd", cfg["repo_path"])
    timeout = min(cfg["max_run_seconds"], max(1, int(command.get("timeout_seconds", 120))))

    if not isinstance(exe, str) or not exe.strip():
        raise ValueError("executable is required")
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        raise ValueError("args must be a list of strings")

    exe_name = Path(exe).name.lower()
    allowed = {str(x).lower() for x in cfg["allowed_executables"]}
    if exe_name not in allowed:
        raise PermissionError(f"executable not allowed: {exe_name}")

    resolved_exe = shutil.which(exe)
    if not resolved_exe:
        raise FileNotFoundError(f"executable not found in PATH: {exe}")

    cwd = safe_path(cwd_raw, [Path(x) for x in cfg["allowed_roots"]])
    if not cwd.is_dir():
        raise NotADirectoryError(str(cwd))

    env = os.environ.copy()
    env["CI"] = "1"
    r = subprocess.run(
        [resolved_exe, *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        shell=False,
        env=env,
    )
    return {
        "returncode": r.returncode,
        "stdout": output_limit(r.stdout),
        "stderr": output_limit(r.stderr),
        "executable": resolved_exe,
        "cwd": str(cwd),
    }


def dispatch(command: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    op = command.get("operation")
    if op == "ping":
        return {"bridge_version": BRIDGE_VERSION, "status": "ok"}
    if op == "status":
        bridge_repo = Path(cfg["bridge_repo_path"])
        return {
            "bridge_version": BRIDGE_VERSION,
            "branch": current_branch(bridge_repo),
            "configured_branch": cfg["branch"],
            "armed": armed(cfg),
            "repo_path": cfg["repo_path"],
            "bridge_repo_path": str(bridge_repo),
            "allowed_roots": cfg["allowed_roots"],
            "allowed_executables": cfg["allowed_executables"],
        }
    if op == "read_file":
        return op_read_file(command, cfg)
    if op == "list_dir":
        return op_list_dir(command, cfg)
    if op == "write_file":
        return op_write_file(command, cfg)
    if op == "delete_file":
        return op_delete_file(command, cfg)
    if op == "mkdir":
        return op_mkdir(command, cfg)
    if op == "run":
        return op_run(command, cfg)
    raise ValueError(f"unsupported operation: {op!r}")


def validate_command(command: Any) -> dict[str, Any]:
    if not isinstance(command, dict):
        raise ValueError("command must be a JSON object")
    command_id = command.get("id")
    if not isinstance(command_id, str) or not command_id.strip():
        raise ValueError("command id is required")
    if "/" in command_id or "\\" in command_id or ".." in command_id:
        raise ValueError("invalid command id")
    return command


def process_inbox(repo: Path, cfg: dict[str, Any]) -> bool:
    inbox = repo / "bridge" / "inbox"
    outbox = repo / "bridge" / "outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)

    changed = False
    for path in sorted(inbox.glob("*.json")):
        if not path.is_file():
            continue
        log(f"processing {path.name}")
        result: dict[str, Any] = {"ok": False, "id": path.stem, "bridge_version": BRIDGE_VERSION}
        try:
            command = validate_command(json.loads(path.read_text(encoding="utf-8")))
            result["id"] = command["id"]
            result["operation"] = command.get("operation")
            result["result"] = dispatch(command, cfg)
            result["ok"] = True
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            result["traceback"] = output_limit(traceback.format_exc())

        result["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        (outbox / f"{path.stem}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        path.unlink()
        changed = True

    if not changed:
        return False

    r = run_git(repo, ["add", "bridge/inbox", "bridge/outbox"])
    if r.returncode != 0:
        raise RuntimeError(f"git add failed: {r.stderr.strip()}")

    r = run_git(
        repo,
        ["-c", "user.name=Masoud Windows Bridge",
         "-c", "user.email=bridge@localhost",
         "commit", "-m", "bridge: process command"],
    )
    if r.returncode != 0:
        combined = (r.stdout + "\n" + r.stderr).strip()
        if "nothing to commit" not in combined.lower():
            raise RuntimeError(f"git commit failed: {combined}")

    r = run_git(repo, ["pull", "--rebase", "--autostash", "origin", cfg["branch"]], timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"git pull --rebase failed: {r.stderr.strip() or r.stdout.strip()}")

    r = run_git(repo, ["push", "origin", f"HEAD:{cfg['branch']}"], timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"git push failed: {r.stderr.strip() or r.stdout.strip()}")

    return True


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    cfg = load_config(repo_root)
    repo = Path(cfg["bridge_repo_path"]).resolve()

    log(f"Masoud Windows Bridge {BRIDGE_VERSION}")
    log(f"bridge_repo={repo}")
    log(f"workspace_repo={cfg['repo_path']}")
    log(f"branch={cfg['branch']}")

    if not (repo / ".git").exists():
        log("ERROR: repo_path is not a Git repository")
        return 2

    branch = current_branch(repo)
    if branch != cfg["branch"]:
        log(f"ERROR: current branch is {branch!r}; expected {cfg['branch']!r}")
        return 3

    log("write/run operations: " + ("ARMED" if armed(cfg) else "DISARMED"))

    while True:
        try:
            git_sync(repo, cfg["branch"])
            process_inbox(repo, cfg)
        except KeyboardInterrupt:
            log("stopped")
            return 0
        except Exception as exc:
            log(f"ERROR: {type(exc).__name__}: {exc}")
        time.sleep(cfg["poll_seconds"])


if __name__ == "__main__":
    raise SystemExit(main())
