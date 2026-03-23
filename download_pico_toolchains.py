#!/usr/bin/env python3
"""
Download Arm GCC, RISC-V GCC, picotool, and pico-sdk-tools bundles for a Pico SDK version,
using versionBundles.json and supportedToolchains.ini (same inputs as the VS Code Pico extension).

By default those two files are fetched from the published Pico VS Code extension data URL.

Example:
  python download_pico_toolchains.py 2.2.0 --output ~/pico-downloads
  python download_pico_toolchains.py 2.2.0 --platform linux_x64
  python download_pico_toolchains.py 2.2.0 --extension-data-url https://raspberrypi.github.io/pico-vscode/0.17.0/
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from configparser import ConfigParser
from io import StringIO
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_EXTENSION_DATA_URL = "https://raspberrypi.github.io/pico-vscode/0.18.0"

# Asset suffixes on raspberrypi/pico-sdk-tools (match extension / GitHub release layout)
_PICO_SDK_TOOLS_ASSETS: dict[str, tuple[str, str]] = {
    "linux_x64": ("pico-sdk-tools-{sdk}-x86_64-lin.tar.gz", ".tar.gz"),
    "linux_arm64": ("pico-sdk-tools-{sdk}-aarch64-lin.tar.gz", ".tar.gz"),
    "darwin_arm64": ("pico-sdk-tools-{sdk}-mac.zip", ".zip"),
    "darwin_x64": ("pico-sdk-tools-{sdk}-mac.zip", ".zip"),
    "win32_x64": ("pico-sdk-tools-{sdk}-x64-win.zip", ".zip"),
}

_PICOTOOL_ASSETS: dict[str, tuple[str, str]] = {
    "linux_x64": ("picotool-{pv}-x86_64-lin.tar.gz", ".tar.gz"),
    "linux_arm64": ("picotool-{pv}-aarch64-lin.tar.gz", ".tar.gz"),
    "darwin_arm64": ("picotool-{pv}-mac.zip", ".zip"),
    "darwin_x64": ("picotool-{pv}-mac.zip", ".zip"),
    "win32_x64": ("picotool-{pv}-x64-win.zip", ".zip"),
}

GITHUB_PICO_SDK_TOOLS = "https://github.com/raspberrypi/pico-sdk-tools"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def fetch_url_text(url: str, timeout: int = 120) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "download_pico_toolchains.py"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def parse_toolchains_ini_text(text: str) -> ConfigParser:
    cp = ConfigParser()
    cp.read_file(StringIO(text))
    return cp


def parse_toolchains_ini(path: Path) -> ConfigParser:
    with path.open(encoding="utf-8") as f:
        return parse_toolchains_ini_text(f.read())


def detect_platform_key() -> str:
    import platform

    system = sys.platform
    machine = platform.machine().lower()
    if system == "win32":
        return "win32_x64"
    if system == "darwin":
        return "darwin_arm64" if machine in ("arm64", "aarch64") else "darwin_x64"
    # Linux and others
    if machine in ("aarch64", "arm64"):
        return "linux_arm64"
    return "linux_x64"


def merge_modifiers(bundle: dict, platform_key: str) -> dict:
    out = dict(bundle)
    mods = bundle.get("modifiers") or {}
    plat = mods.get(platform_key) or {}
    for k, v in plat.items():
        out[k] = v
    return out


def extract_pico_sdk_tools_tag_from_riscv_url(url: str) -> str | None:
    """e.g. .../download/v2.2.0-3/riscv-... -> 'v2.2.0-3'."""
    m = re.search(r"/releases/download/(v[\d.]+-\d+)/", url)
    return m.group(1) if m else None


def resolve_pico_sdk_tools_tag(
    sdk_version: str,
    riscv_key: str,
    ini: ConfigParser,
    override: str | None,
) -> str:
    if override:
        return override if override.startswith("v") else f"v{override}"
    if riscv_key and riscv_key.upper() != "NONE" and ini.has_section(riscv_key):
        url = ini.get(riscv_key, "linux_x64", fallback="")
        tag = extract_pico_sdk_tools_tag_from_riscv_url(url)
        if tag:
            return tag
    # Older bundles without RISC-V: common convention used by the extension
    return f"v{sdk_version}-0"


def download(url: str, dest: Path, chunk: int = 1 << 20) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "download_pico_toolchains.py"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        total = resp.headers.get("Content-Length")
        nread = 0
        with dest.open("wb") as out:
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                out.write(buf)
                nread += len(buf)
        if total:
            print(f"  wrote {dest.name} ({nread} bytes)")


def filename_suffix_from_url(url: str) -> str:
    """Extension from the URL's last path segment, including .tar.* for tarballs."""
    seg = url.rstrip("/").split("/")[-1]
    p = Path(seg)
    suf = p.suffix
    if suf and seg.lower().endswith(".tar" + suf.lower()):
        return ".tar" + suf
    return suf


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Download Pico toolchains and tools for an SDK version (from versionBundles + supportedToolchains.ini)."
    )
    ap.add_argument("sdk_version", help="SDK version key, e.g. 2.2.0")
    ap.add_argument(
        "--extension-data-url",
        default=DEFAULT_EXTENSION_DATA_URL,
        metavar="URL",
        help=f"Base URL for versionBundles.json and supportedToolchains.ini "
        f"(default: {DEFAULT_EXTENSION_DATA_URL}). Trailing slash optional.",
    )
    ap.add_argument(
        "--bundles",
        type=Path,
        default=None,
        help="Use a local versionBundles.json instead of fetching from --extension-data-url",
    )
    ap.add_argument(
        "--toolchains-ini",
        type=Path,
        default=None,
        help="Use a local supportedToolchains.ini instead of fetching from --extension-data-url",
    )
    ap.add_argument(
        "--platform",
        choices=sorted(_PICO_SDK_TOOLS_ASSETS.keys()),
        help="Target platform key (default: detect this machine)",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("pico-tool-downloads"),
        help="Output directory (default: ./pico-tool-downloads)",
    )
    ap.add_argument(
        "--pico-sdk-tools-tag",
        metavar="TAG",
        help="GitHub tag for raspberrypi/pico-sdk-tools (e.g. v2.2.0-3). "
        "Default: parsed from RISC-V URL in supportedToolchains.ini, else vSDK-0",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print URLs and paths only",
    )
    args = ap.parse_args()

    sdk_version = args.sdk_version.strip()
    base = args.extension_data_url.rstrip("/")

    if args.bundles is not None:
        if not args.bundles.is_file():
            print(f"Missing bundles file: {args.bundles}", file=sys.stderr)
            return 1
        bundles = load_json(args.bundles)
    else:
        bundles_url = f"{base}/versionBundles.json"
        try:
            bundles = json.loads(fetch_url_text(bundles_url))
        except urllib.error.HTTPError as e:
            print(f"Failed to fetch {bundles_url}: HTTP {e.code}", file=sys.stderr)
            return 1
        except OSError as e:
            print(f"Failed to fetch {bundles_url}: {e}", file=sys.stderr)
            return 1

    if args.toolchains_ini is not None:
        if not args.toolchains_ini.is_file():
            print(f"Missing toolchains file: {args.toolchains_ini}", file=sys.stderr)
            return 1
        ini = parse_toolchains_ini(args.toolchains_ini)
    else:
        ini_url = f"{base}/supportedToolchains.ini"
        try:
            ini = parse_toolchains_ini_text(fetch_url_text(ini_url))
        except urllib.error.HTTPError as e:
            print(f"Failed to fetch {ini_url}: HTTP {e.code}", file=sys.stderr)
            return 1
        except OSError as e:
            print(f"Failed to fetch {ini_url}: {e}", file=sys.stderr)
            return 1

    if args.bundles is None:
        print(f"Using versionBundles.json from {base}/versionBundles.json")
    if args.toolchains_ini is None:
        print(f"Using supportedToolchains.ini from {base}/supportedToolchains.ini")
    if args.bundles is None or args.toolchains_ini is None:
        print()
    if sdk_version not in bundles:
        print(f"Unknown SDK version {sdk_version!r}. Known: {', '.join(sorted(bundles))}", file=sys.stderr)
        return 1

    platform_key = args.platform or detect_platform_key()
    bundle = merge_modifiers(bundles[sdk_version], platform_key)

    arm_key = bundle["toolchain"]
    riscv_key = bundle.get("riscvToolchain") or "NONE"
    picotool_ver = bundle["picotool"]

    if not ini.has_section(arm_key):
        print(f"No [{arm_key}] in supportedToolchains.ini", file=sys.stderr)
        return 1

    arm_url = ini.get(arm_key, platform_key, fallback="")
    if not arm_url:
        print(f"No URL for Arm toolchain [{arm_key}] {platform_key}", file=sys.stderr)
        return 1

    out_root = args.output
    jobs: list[tuple[str, str, Path]] = []

    arm_ext = filename_suffix_from_url(arm_url)
    jobs.append(
        ("Arm GCC", arm_url, out_root / "arm-toolchain" / f"arm-toolchain{arm_ext}")
    )

    if riscv_key.upper() != "NONE":
        if not ini.has_section(riscv_key):
            print(f"No [{riscv_key}] in supportedToolchains.ini", file=sys.stderr)
            return 1
        rv_url = ini.get(riscv_key, platform_key, fallback="")
        if not rv_url:
            print(f"No URL for RISC-V [{riscv_key}] {platform_key}", file=sys.stderr)
            return 1
        rv_ext = filename_suffix_from_url(rv_url)
        jobs.append(("RISC-V GCC", rv_url, out_root / "riscv-toolchain" / f"riscv-toolchain{rv_ext}"))

    tag = resolve_pico_sdk_tools_tag(sdk_version, riscv_key, ini, args.pico_sdk_tools_tag)
    sdk_maj_min_patch = sdk_version  # filename uses 2.2.0

    pts_tmpl, _ = _PICO_SDK_TOOLS_ASSETS[platform_key]
    pt_tmpl, _ = _PICOTOOL_ASSETS[platform_key]
    pts_name = pts_tmpl.format(sdk=sdk_maj_min_patch)
    pt_name = pt_tmpl.format(pv=picotool_ver)

    pts_url = f"{GITHUB_PICO_SDK_TOOLS}/releases/download/{tag}/{pts_name}"
    pt_url = f"{GITHUB_PICO_SDK_TOOLS}/releases/download/{tag}/{pt_name}"
    pts_ext = filename_suffix_from_url(pts_url)
    pt_ext = filename_suffix_from_url(pt_url)
    jobs.append(
        ("pico-sdk-tools", pts_url, out_root / "pico-sdk-tools" / f"pico-sdk-tools{pts_ext}")
    )
    jobs.append(("picotool", pt_url, out_root / "picotool" / f"picotool{pt_ext}"))

    print(f"SDK {sdk_version}  platform {platform_key}  pico-sdk-tools tag {tag}")
    print(f"  picotool version string: {picotool_ver}")
    print(f"  Arm toolchain key: {arm_key}")
    if riscv_key.upper() != "NONE":
        print(f"  RISC-V toolchain key: {riscv_key}")
    else:
        print("  RISC-V toolchain key: NONE (skipped)")
    print()

    for label, url, path in jobs:
        print(f"{label}:")
        print(f"  {url}")
        print(f"  -> {path}")
        if not args.dry_run:
            try:
                download(url, path)
            except urllib.error.HTTPError as e:
                print(f"  HTTP {e.code}: {e.reason}", file=sys.stderr)
                if e.code == 404:
                    print(
                        "  Hint: check --pico-sdk-tools-tag (e.g. v2.2.0-3 from supportedToolchains.ini RISC-V URL).",
                        file=sys.stderr,
                    )
                return 1
            except OSError as e:
                print(f"  Error: {e}", file=sys.stderr)
                return 1
        print()

    if args.dry_run:
        print("(dry-run: no files downloaded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
