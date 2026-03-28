#!/usr/bin/env python3
"""Cross-platform skill installer for Weekend Scout.

Copies the generated skill files to the user's global skill directory for one
or more agent platforms, then optionally installs the Python package and
pre-downloads GeoNames data.

Usage:
    python install/install_skill.py                        # auto-detect platform
    python install/install_skill.py --platform claude-code # specific platform
    python install/install_skill.py --platform all         # all platforms
    python install/install_skill.py --with-pip             # also run pip install -e .
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Source directories inside the repo (relative to repo root)
SOURCE_DIRS: dict[str, str] = {
    "claude-code": ".claude/skills/weekend-scout",
    "codex":       ".codex/skills/weekend-scout",
    "openclaw":    ".openclaw/skills/weekend-scout",
}

# User-scoped global installation directories
INSTALL_TARGETS: dict[str, Path] = {
    "claude-code": Path.home() / ".claude"   / "skills" / "weekend-scout",
    "codex":       Path.home() / ".codex"    / "skills" / "weekend-scout",
    "openclaw":    Path.home() / ".openclaw" / "skills" / "weekend-scout",
}

# Parent dirs used for auto-detection (platform is installed if this dir exists)
PLATFORM_HOME_DIRS: dict[str, Path] = {
    "claude-code": Path.home() / ".claude",
    "codex":       Path.home() / ".codex",
    "openclaw":    Path.home() / ".openclaw",
}

INVOKE_CMDS: dict[str, str] = {
    "claude-code": "/weekend-scout",
    "codex":       "$weekend-scout",
    "openclaw":    "weekend-scout",
}


def detect_platforms() -> list[str]:
    """Auto-detect which platforms are installed based on home dirs.

    Returns:
        List of platform IDs to install to. Falls back to ['claude-code'] if none detected.
    """
    detected = [p for p, d in PLATFORM_HOME_DIRS.items() if d.exists()]
    if not detected:
        print("No platform home directories found — defaulting to claude-code.")
        return ["claude-code"]
    if len(detected) > 1:
        names = ", ".join(detected)
        print(f"Multiple platforms detected: {names} — installing to all.")
    return detected


def install_platform(platform: str, repo_root: Path) -> bool:
    """Copy skill files from repo to the user's global skill directory.

    Args:
        platform: Platform identifier.
        repo_root: Absolute path to the repo root.

    Returns:
        True on success, False on failure.
    """
    source = repo_root / SOURCE_DIRS[platform]
    target = INSTALL_TARGETS[platform]

    if not source.exists():
        print(f"  ERROR: source directory not found: {source}")
        print(f"  Run: python skill_template/generate.py --platform {platform}")
        return False

    target.mkdir(parents=True, exist_ok=True)

    # Copy all files from source to target
    for item in source.rglob("*"):
        if item.is_file():
            rel = item.relative_to(source)
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)

    print(f"  Installed to: {target}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install the Weekend Scout skill to your agent platform."
    )
    parser.add_argument(
        "--platform",
        metavar="NAME",
        help=(
            "Platform to install to: claude-code, codex, openclaw, or 'all'. "
            "Default: auto-detect from installed platform home directories."
        ),
    )
    parser.add_argument(
        "--with-pip",
        action="store_true",
        help="Also run 'pip install -e .' to install the Python package.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    # Determine target platforms
    if args.platform == "all":
        platforms = list(SOURCE_DIRS.keys())
    elif args.platform:
        if args.platform not in SOURCE_DIRS:
            print(f"Error: unknown platform '{args.platform}'.", file=sys.stderr)
            print(f"Available: {', '.join(SOURCE_DIRS)} or 'all'", file=sys.stderr)
            sys.exit(1)
        platforms = [args.platform]
    else:
        platforms = detect_platforms()

    # Optionally install the Python package
    if args.with_pip:
        print("Installing Python package...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(repo_root)],
            check=False,
        )
        if result.returncode != 0:
            print("WARNING: pip install failed. Continuing with skill installation.")
        else:
            print("  Package installed.")

    # Install each platform
    all_ok = True
    for platform in platforms:
        print(f"\nInstalling skill for {platform}...")
        ok = install_platform(platform, repo_root)
        if not ok:
            all_ok = False

    if not all_ok:
        print("\nSome platforms failed — see errors above.")
        sys.exit(1)

    # Pre-download GeoNames data
    print("\nPre-downloading GeoNames city data...")
    result = subprocess.run(
        [sys.executable, "-m", "weekend_scout", "download-data"],
        check=False,
    )
    if result.returncode != 0:
        print("WARNING: GeoNames download failed. Data will be downloaded on first run.")

    # Print next steps
    print("\n" + "=" * 50)
    print("Weekend Scout installed successfully!")
    print("\nNext steps:")
    for platform in platforms:
        cmd = INVOKE_CMDS[platform]
        print(f"  {platform}: type '{cmd}' to start scouting")
    print("=" * 50)


if __name__ == "__main__":
    main()
