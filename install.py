#!/usr/bin/env python3
"""Install the allowlisted user-level Codex prompt, skills, and Ponytail plugin."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone


KIT_ROOT = Path(__file__).resolve().parent
PAYLOAD_ROOT = KIT_ROOT / "payload"
MANIFEST_PATH = KIT_ROOT / "MANIFEST.json"
CHECKSUM_PATH = KIT_ROOT / "payload.sha256"
PONYTAIL_URL = "https://github.com/DietrichGebert/ponytail.git"
PONYTAIL_REF = "96608e078b2d5ea607c5c3b8b5a54d1c1fba6846"
PONYTAIL_VERSION = "5.3.3"
PONYTAIL_ID = "ponytail@ponytail"


class KitError(Exception):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest():
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KitError("MANIFEST.json is missing or invalid.") from exc
    expected_skills = {
        "ai-image-generation",
        "goal-keepalive",
        "codex-agent-orchestration",
        "codex-reasoning-quality-gates",
        "karpathy-guidelines",
        "review-ready-report",
        "html-delivery",
        "html-effectiveness",
    }
    if set(data.get("skills", [])) != expected_skills:
        raise KitError("The skill allowlist in MANIFEST.json does not match this installer.")
    plugin = data.get("plugin", {})
    if (
        plugin.get("id") != PONYTAIL_ID
        or plugin.get("version") != PONYTAIL_VERSION
        or plugin.get("repository") != PONYTAIL_URL
        or plugin.get("ref") != PONYTAIL_REF
        or plugin.get("marketplace_sparse_path") != ".agents/plugins"
    ):
        raise KitError("The Ponytail source pin in MANIFEST.json is invalid.")
    if set(data.get("codex_global_files", [])) != {"AGENTS.md", "RTK.md"}:
        raise KitError("The global prompt file allowlist in MANIFEST.json is invalid.")
    return data


def validate_payload(manifest):
    if not CHECKSUM_PATH.is_file():
        raise KitError("payload.sha256 is missing.")
    checked = {}
    for line_number, line in enumerate(CHECKSUM_PATH.read_text(encoding="ascii").splitlines(), 1):
        if not line.strip():
            continue
        expected, separator, relative_name = line.partition("  ")
        if not separator or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise KitError("Invalid checksum entry on line %d." % line_number)
        relative = PurePosixPath(relative_name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in relative_name:
            raise KitError("Unsafe payload path in checksum list: %s" % relative_name)
        source = KIT_ROOT.joinpath(*relative.parts)
        if not source.resolve().is_relative_to(PAYLOAD_ROOT.resolve()) or not source.is_file():
            raise KitError("Checksum entry is missing or outside the payload: %s" % relative_name)
        if relative_name in checked:
            raise KitError("Duplicate checksum entry: %s" % relative_name)
        actual = sha256_file(source)
        if actual != expected:
            raise KitError("Payload checksum mismatch: %s" % relative_name)
        checked[relative_name] = actual

    actual_files = set()
    for path in PAYLOAD_ROOT.rglob("*"):
        if path.is_symlink():
            raise KitError("Symlinks are not allowed in the install payload: %s" % path.name)
        if path.is_file():
            actual_files.add(path.relative_to(KIT_ROOT).as_posix())
    if actual_files != set(checked):
        raise KitError("The checksum list and payload file set do not match.")

    required = {"payload/global/AGENTS.md", "payload/global/RTK.md"}
    for name in manifest["skills"]:
        required.add("payload/skills/%s/SKILL.md" % name)
    if not required.issubset(actual_files):
        raise KitError("A required prompt or skill entry file is missing.")
    if "payload/skills/html-effectiveness/LICENSE" not in actual_files:
        raise KitError("html-effectiveness must retain its upstream Apache-2.0 license.")
    return checked


def codex_home():
    value = os.environ.get("CODEX_HOME")
    return Path(value).expanduser().resolve() if value else (Path.home() / ".codex").resolve()


def run_command(args, timeout=30):
    invocation = list(args)
    if invocation and invocation[0] == "codex" and os.name == "nt":
        launcher = shutil.which("codex.ps1") or shutil.which("codex")
        if launcher and launcher.lower().endswith(".ps1"):
            shell = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
            invocation = [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", launcher] + invocation[1:]
    try:
        result = subprocess.run(invocation, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise KitError("Could not run %s." % args[0]) from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        detail = re.sub(r"(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]+", "[redacted]", detail)
        raise KitError("%s failed (exit %d): %s" % (args[0], result.returncode, detail[:600]))
    return result.stdout.strip()


def run_json(args):
    output = run_command(args)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise KitError("%s did not return valid JSON." % args[0]) from exc


def plugin_state():
    listing = run_json(["codex", "plugin", "list", "--json"])
    installed = listing.get("installed", [])
    return [item for item in installed if item.get("name") == "ponytail" or item.get("pluginId", "").startswith("ponytail@")]


def marketplace_state():
    listing = run_json(["codex", "plugin", "marketplace", "list", "--json"])
    return listing.get("marketplaces", [])


def inspect_ponytail():
    markets = marketplace_state()
    market = next((item for item in markets if item.get("name") == "ponytail"), None)
    plugins = plugin_state()
    plugin = next((item for item in plugins if item.get("pluginId") == PONYTAIL_ID), None)

    if len(plugins) > (1 if plugin else 0):
        raise KitError("More than one Ponytail marketplace entry is installed; review it before changing plugin state.")
    if market is None:
        if plugin:
            raise KitError("Ponytail is installed but its marketplace is not registered; preserving the current state.")
        return True

    source = market.get("marketplaceSource", {})
    url = source.get("source", "").removesuffix(".git")
    if source.get("sourceType") != "git" or url != PONYTAIL_URL.removesuffix(".git"):
        raise KitError("A different marketplace already uses the name ponytail; preserving it and its plugins.")

    root = market.get("root")
    if not root or not Path(root).is_dir():
        raise KitError("The Ponytail marketplace snapshot is unavailable; preserving the current state.")
    commit = run_command(["git", "-C", root, "rev-parse", "HEAD"])
    if commit.lower() != PONYTAIL_REF:
        raise KitError("The registered Ponytail marketplace points to another commit; review dependent plugins before replacing it.")

    if plugin:
        source_url = plugin.get("source", {}).get("url", "").removesuffix(".git")
        if plugin.get("version") != PONYTAIL_VERSION or not plugin.get("enabled") or source_url != PONYTAIL_URL.removesuffix(".git"):
            raise KitError("Ponytail is installed with a different version, source, or enabled state; preserving it.")
        return False
    return True


def same_entry(left, right):
    if left.is_symlink() or right.is_symlink():
        return left.is_symlink() and right.is_symlink() and os.readlink(left) == os.readlink(right)
    if left.is_file() and right.is_file():
        return sha256_file(left) == sha256_file(right)
    if not left.is_dir() or not right.is_dir():
        return False
    left_items = {p.relative_to(left).as_posix(): p for p in left.rglob("*") if p.is_file() or p.is_symlink()}
    right_items = {p.relative_to(right).as_posix(): p for p in right.rglob("*") if p.is_file() or p.is_symlink()}
    if left_items.keys() != right_items.keys():
        return False
    return all(same_entry(left_items[name], right_items[name]) for name in left_items)


def remove_entry(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def copy_entry(source, destination):
    if source.is_dir() and not source.is_symlink():
        shutil.copytree(source, destination, symlinks=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination, follow_symlinks=False)


def backup_entry(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy_entry(source, destination)
    if not same_entry(source, destination):
        remove_entry(destination)
        raise KitError("Could not verify a local backup for %s." % source.name)


def make_jobs(manifest):
    home = Path.home().resolve()
    codex = codex_home()
    canonical_skills = home / ".agents" / "skills"
    legacy_skills = codex / "skills"
    jobs = []
    for name in manifest["codex_global_files"]:
        jobs.append({
            "source": PAYLOAD_ROOT / "global" / name,
            "target": codex / name,
            "backup": Path("codex") / name,
            "remove_only": False,
        })
    for name in manifest["skills"]:
        jobs.append({
            "source": PAYLOAD_ROOT / "skills" / name,
            "target": canonical_skills / name,
            "backup": Path("agents") / "skills" / name,
            "remove_only": False,
        })
        legacy = legacy_skills / name
        if legacy.resolve() != (canonical_skills / name).resolve() and (legacy.exists() or legacy.is_symlink()):
            jobs.append({
                "source": None,
                "target": legacy,
                "backup": Path("codex") / "skills" / name,
                "remove_only": True,
            })
    return jobs


def check_destinations(jobs):
    for job in jobs:
        target = job["target"]
        if target.is_symlink():
            raise KitError("Refusing to replace a symbolic-link target: %s" % target.name)
        if not target.exists():
            continue
        expected_directory = job["source"] is not None and job["source"].is_dir()
        if job["remove_only"]:
            expected_directory = True
        if expected_directory != target.is_dir():
            raise KitError("A target has an unexpected file type: %s" % target.name)


def backup_root_for(codex, has_changes):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = codex / "global-config-kit-backups" / stamp
    suffix = 1
    while root.exists():
        root = codex / "global-config-kit-backups" / (stamp + "-%d" % suffix)
        suffix += 1
    if has_changes:
        root.mkdir(parents=True, exist_ok=False)
    return root


def install_files(jobs, backup_root):
    prepared = []
    for index, job in enumerate(jobs):
        target = job["target"]
        source = job["source"]
        if job["remove_only"]:
            if target.exists():
                prepared.append((job, None, True))
            continue
        if target.exists() and same_entry(source, target):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = target.parent / (".%s.kit-stage-%d-%d" % (target.name, os.getpid(), index))
        if stage.exists() or stage.is_symlink():
            raise KitError("A temporary installation path already exists: %s" % stage.name)
        copy_entry(source, stage)
        if not same_entry(source, stage):
            remove_entry(stage)
            raise KitError("Could not stage %s for installation." % target.name)
        prepared.append((job, stage, target.exists()))

    completed = []
    try:
        for job, stage, existed in prepared:
            target = job["target"]
            backup = backup_root / job["backup"]
            if existed:
                backup_entry(target, backup)
                remove_entry(target)
                completed.append((target, backup))
            else:
                completed.append((target, None))
            if stage is not None:
                os.replace(stage, target)
    except Exception:
        for target, backup in reversed(completed):
            if target.exists() or target.is_symlink():
                remove_entry(target)
            if backup and backup.exists():
                copy_entry(backup, target)
        for _, stage, _ in prepared:
            if stage and (stage.exists() or stage.is_symlink()):
                remove_entry(stage)
        raise
    return len(prepared)


def backup_config_before_plugin(codex, backup_root):
    config = codex / "config.toml"
    if not config.is_file():
        return None
    destination = backup_root / "codex" / "config.toml"
    backup_entry(config, destination)
    try:
        if os.name != "nt":
            destination.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return destination


def install_plugin_if_needed(needed, backup_root):
    if not needed:
        return "Ponytail is already installed, enabled, and pinned to the required commit."
    backup = backup_config_before_plugin(codex_home(), backup_root)
    if backup:
        print("Backed up the local Codex config before the native plugin command.")
    markets = marketplace_state()
    market = next((item for item in markets if item.get("name") == "ponytail"), None)
    if market is None:
        run_command([
            "codex", "plugin", "marketplace", "add", PONYTAIL_URL,
            "--ref", PONYTAIL_REF,
            "--sparse", ".agents/plugins",
            "--json",
        ], timeout=180)
    run_command(["codex", "plugin", "add", PONYTAIL_ID, "--json"], timeout=180)
    still_needed = inspect_ponytail()
    if still_needed:
        raise KitError("The Codex CLI command returned, but the pinned Ponytail plugin is not enabled afterward.")
    return "Ponytail is installed and enabled at version 5.3.3 from the pinned upstream commit."


def preflight(manifest):
    if sys.version_info < (3, 10):
        raise KitError("Python 3.10 or newer is required.")
    missing = [name for name in ("git", "codex") if shutil.which(name) is None]
    if missing:
        raise KitError("Missing required command(s): %s." % ", ".join(missing))
    run_command(["codex", "--version"])
    jobs = make_jobs(manifest)
    check_destinations(jobs)
    if not codex_home().exists():
        return jobs, True, False
    run_command(["codex", "plugin", "marketplace", "--help"])
    run_command(["codex", "plugin", "add", "--help"])
    return jobs, inspect_ponytail(), True


def main():
    parser = argparse.ArgumentParser(description="Check or install the allowlisted Codex global prompt kit.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify payload, prerequisites, and current plugin state")
    mode.add_argument("--apply", action="store_true", help="install the prompt files, skills, and pinned Ponytail plugin")
    parser.add_argument("--yes", action="store_true", help="confirm the exact allowlisted changes without an interactive prompt")
    args = parser.parse_args()

    try:
        manifest = load_manifest()
        checked = validate_payload(manifest)
        jobs, plugin_needed, codex_home_exists = preflight(manifest)
        print("Payload integrity: OK (%d files, SHA-256 verified)." % len(checked))
        print("Codex home: %s" % codex_home())
        print("User skill destination: %s" % (Path.home() / ".agents" / "skills"))
        print("RTK CLI: %s" % ("available" if shutil.which("rtk") else "not found (optional)"))
        print("CodeGraph CLI: %s" % ("available" if shutil.which("codegraph") else "not found (optional; prompt fallback remains)"))
        if not codex_home_exists:
            print("Codex home: not initialized yet; --apply will create the empty directory after confirmation.")
        print("Ponytail: %s" % ("will be installed from pinned source" if plugin_needed else "already installed at pinned source"))

        if args.check:
            print("Preflight: OK. No files or plugin settings were changed.")
            return 0
        if not args.yes:
            answer = input("Install the two global prompt files and eight skills, keeping local backups, and install Ponytail? [y/N] ")
            if answer.strip().lower() not in {"y", "yes"}:
                print("Cancelled; no changes made.")
                return 0

        if not codex_home_exists:
            codex_home().mkdir(parents=True, exist_ok=True)
            run_command(["codex", "plugin", "marketplace", "--help"])
            run_command(["codex", "plugin", "add", "--help"])
        check_destinations(jobs)
        has_changes = any(
            job["remove_only"]
            or not job["target"].exists()
            or not same_entry(job["source"], job["target"])
            for job in jobs
        ) or plugin_needed
        backup_root = backup_root_for(codex_home(), has_changes)
        changed = install_files(jobs, backup_root)
        print("Installed or reconciled %d global file/skill entries." % changed)
        try:
            plugin_result = install_plugin_if_needed(plugin_needed, backup_root)
        except KitError as exc:
            print("Global prompt and skills are installed, but Ponytail needs attention: %s" % exc, file=sys.stderr)
            print("The local backup remains at: %s" % backup_root, file=sys.stderr)
            return 4
        print(plugin_result)
        print("Post-install check: rerun `python install.py --check`; restart Codex if the current session has not reloaded the files.")
        if has_changes:
            print("Local backup directory: %s" % backup_root)
        return 0
    except KitError as exc:
        print("Preflight/install stopped: %s" % exc, file=sys.stderr)
        return 2
    except (OSError, shutil.Error, subprocess.SubprocessError) as exc:
        print("Install failed safely: %s" % type(exc).__name__, file=sys.stderr)
        print("Review the local backup directory before retrying.", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
