"""T7: the shim prevents the evals-neighbor dependency shadow."""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

PROBE = textwrap.dedent(
    """
    import sentinel_dep
    import satyrn_evals
    print(sentinel_dep.__file__)
    print(satyrn_evals.__file__)
    """
)


def _make_env_dirs(tmp_path: Path):
    """evals site-packages (with a conflicting dep) vs the locked env."""
    shadow_site = tmp_path / "shadow_site"  # the OLD PYTHONPATH target
    package = shadow_site / "satyrn_evals"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    dep = shadow_site / "sentinel_dep"
    dep.mkdir()
    (dep / "__init__.py").write_text("MARK = 'shadow'")
    locked_site = tmp_path / "locked_site"  # the oracle venv's site-packages
    dep = locked_site / "sentinel_dep"
    dep.mkdir(parents=True)
    (dep / "__init__.py").write_text("MARK = 'locked'")
    return shadow_site, package, locked_site


def test_shim_keeps_the_locked_env_in_charge(tmp_path: Path) -> None:
    shadow_site, package, locked_site = _make_env_dirs(tmp_path)
    script = tmp_path / "probe.py"
    script.write_text(PROBE)

    # OLD behavior: PYTHONPATH = evals' site-packages, shadow first
    old_env = dict(os.environ)
    old_env["PYTHONPATH"] = os.fspath(shadow_site) + os.pathsep + os.fspath(locked_site)
    old_out = subprocess.run(
        [sys.executable, "-S", str(script)], env=old_env,
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert "shadow" in old_out[0]  # the hazard is real: shadow wins

    # NEW behavior: PYTHONPATH = shim (only satyrn_evals), locked env second
    shim = tmp_path / "hookpath"
    shim.mkdir()
    (shim / "satyrn_evals").symlink_to(package, target_is_directory=True)
    new_env = dict(os.environ)
    new_env["PYTHONPATH"] = os.fspath(shim) + os.pathsep + os.fspath(locked_site)
    new_out = subprocess.run(
        [sys.executable, "-S", str(script)], env=new_env,
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert os.fspath(locked_site) in new_out[0]  # dep from the locked env
    # evals imported THROUGH the shim symlink to the running package
    assert new_out[1].startswith(os.fspath(shim))
    assert Path(new_out[1]).resolve() == (package / "__init__.py").resolve()
