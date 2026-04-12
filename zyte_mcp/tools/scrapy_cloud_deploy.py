"""Scrapy Cloud deploy tool."""

from __future__ import annotations

import asyncio
import json
import os
import re
import tomllib
import urllib.request
from asyncio.subprocess import PIPE
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from zyte_mcp.scrapy_cloud_config import _get_scrapy_cloud_api_key


_SCRAPY_RELEASES_URL = (
    "https://api.github.com/repos/scrapy/scrapy/releases/latest"
)


async def _fetch_latest_scrapy_version() -> str | None:
    """Return the latest Scrapy major.minor version from GitHub (e.g. '2.15').

    Returns None on any error so callers can fall back gracefully.
    """
    loop = asyncio.get_event_loop()

    def _fetch() -> str | None:
        try:
            req = urllib.request.Request(
                _SCRAPY_RELEASES_URL,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "zyte-mcp"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    return None
                data = json.loads(resp.read())
            tag = data.get("tag_name", "")
            m = re.match(r"(\d+\.\d+)", tag)
            return m.group(1) if m else None
        except Exception:
            return None

    return await loop.run_in_executor(None, _fetch)


def register_scrapy_cloud_deploy_tool(server: FastMCP) -> None:
    @server.tool(description="Deploy a Scrapy project to Scrapy Cloud using shub")
    async def scrapy_cloud_deploy(
        project_path: str,
        project_id: int | None = None,
    ) -> dict[str, Any]:
        """Deploy a local Scrapy project to Scrapy Cloud.

        Runs preflight checks before deploying:
        - Verifies shub is installed
        - Verifies project_path contains a Scrapy project (scrapy.cfg)
        - Verifies a target project is known (scrapinghub.yml or project_id)

        If scrapinghub.yml is missing and no project_id is provided, returns
        instructions to create a project at https://app.zyte.com/ first.
        """
        # Preflight 2 needs project_dir, resolve it early so preflight 1 can
        # check for a .venv-local shub before falling back to the system PATH.
        project_dir = Path(project_path)

        # Preflight 1: shub installed?
        # Prefer `uv run shub` when the project has a .venv (shub added as a
        # dev dependency via `uv add shub`), otherwise fall back to system shub.
        shub_cmd: list[str]
        if (project_dir / ".venv").exists():
            shub_cmd = ["uv", "run", "shub"]
        else:
            shub_cmd = ["shub"]

        try:
            version_proc = await asyncio.create_subprocess_exec(
                *shub_cmd, "--version",
                cwd=str(project_dir),
                stdout=PIPE,
                stderr=PIPE,
            )
            await version_proc.communicate()
            if version_proc.returncode != 0:
                return {
                    "ready": False,
                    "issue": "shub_not_installed",
                    "fix": "uv add shub  # or: pip install shub",
                }
        except FileNotFoundError:
            return {
                "ready": False,
                "issue": "shub_not_installed",
                "fix": "uv add shub  # or: pip install shub",
            }

        # Preflight 2: scrapy.cfg present?
        if not (project_dir / "scrapy.cfg").exists():
            return {
                "ready": False,
                "issue": "not_a_scrapy_project",
                "path": str(project_dir.resolve()),
            }

        # Preflight 3: scrapinghub.yml or project_id?
        scrapinghub_yml = project_dir / "scrapinghub.yml"
        if not scrapinghub_yml.exists() and project_id is None:
            return {
                "ready": False,
                "issue": "missing_scrapinghub_yml",
                "action_required": (
                    "Create a Scrapy Cloud project at https://app.zyte.com/, "
                    "then paste the project ID here and call scrapy_cloud_deploy "
                    "again with project_id=<ID>"
                ),
                "template": "projects:\n  default: <YOUR_PROJECT_ID>\n",
            }

        # If a project_id was supplied and no scrapinghub.yml exists yet, create
        # a minimal one together with a requirements.txt derived from pyproject.toml.
        if project_id is not None and not scrapinghub_yml.exists():
            # Parse [project].dependencies from pyproject.toml.
            pyproject = project_dir / "pyproject.toml"
            dependencies: list[str] = []
            scrapy_stack: str | None = None
            if pyproject.exists():
                with pyproject.open("rb") as fh:
                    data = tomllib.load(fh)
                dependencies = data.get("project", {}).get("dependencies", [])

            # Derive the Scrapy Cloud stack from the scrapy dependency (e.g.
            # "scrapy>=2.14.2" → stack "scrapy:2.14") and exclude scrapy itself
            # from requirements.txt — the stack already provides it on the cloud.
            requirements: list[str] = []
            for dep in dependencies:
                name = re.split(r"[>=<!;\[]", dep)[0].strip().lower()
                if name == "scrapy":
                    ver_match = re.search(r"(\d+\.\d+)", dep)
                    if ver_match:
                        scrapy_stack = f"scrapy:{ver_match.group(1)}"
                else:
                    requirements.append(dep)

            # Override with the latest release from GitHub when available so the
            # deployed project always targets the current Scrapy release.
            # Falls back silently to the pyproject.toml-derived version on error.
            github_version = await _fetch_latest_scrapy_version()
            if github_version:
                scrapy_stack = f"scrapy:{github_version}"

            (project_dir / "requirements.txt").write_text(
                "\n".join(requirements) + "\n", encoding="utf-8"
            )

            stack_line = f"stack: {scrapy_stack}\n" if scrapy_stack else ""
            scrapinghub_yml.write_text(
                f"projects:\n  default: {project_id}\n"
                f"{stack_line}"
                "requirements:\n  file: requirements.txt\n",
                encoding="utf-8",
            )

        # Deploy — project ID is now encoded in scrapinghub.yml, not the CLI arg
        cmd = [*shub_cmd, "deploy"]

        env = {**os.environ, "SHUB_APIKEY": _get_scrapy_cloud_api_key()}

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(project_dir),
            env=env,
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        stdout_text = stdout_bytes.decode(errors="replace")
        stderr_text = stderr_bytes.decode(errors="replace")

        # Parse structured fields from shub output
        version_match = re.search(r"Packing version (.+)", stdout_text)
        project_match = re.search(r'project "(\d+)"', stdout_text)

        result: dict[str, Any] = {
            "success": proc.returncode == 0,
            "project_id": int(project_match.group(1)) if project_match else project_id,
            "version": version_match.group(1).strip() if version_match else None,
            "stdout": stdout_text,
            "stderr": stderr_text,
        }

        # On failure, surface any scrapy version mismatch hint from the output.
        if not result["success"]:
            combined = stdout_text + "\n" + stderr_text
            mismatch = re.search(
                r"(?i)(scrapy[^\n]*version[^\n]*mismatch[^\n]*"
                r"|requires scrapy[^\n]*"
                r"|scrapy[^\n]*not supported[^\n]*"
                r"|stack[^\n]*scrapy[^\n]*)",
                combined,
            )
            if mismatch:
                result["scrapy_version_hint"] = mismatch.group(0).strip()

        return result
