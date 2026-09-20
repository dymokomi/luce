#!/usr/bin/env python3
"""Black-box contract tests for `luce run --sandbox`."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LUCE = ROOT / "build" / "luce"


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(LUCE), *arguments], text=True, capture_output=True, check=False
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="luce-sandbox-") as temporary:
        parent = Path(temporary)
        root = parent / "root"
        root.mkdir()
        program = root / "recipe.luc"
        program.write_text(
            'pub func main(arguments: list[str]) -> int!:\n'
            '    print(arguments[0] if arguments.length > 0 else "missing")\n'
            '    return 0\n',
            encoding="utf-8",
        )
        outside = parent / "outside.luc"
        outside.write_text(
            "pub func main(arguments: list[str]) -> int!:\n    return 0\n",
            encoding="utf-8",
        )
        rejected = run("run", "--sandbox", str(root), str(outside))
        assert rejected.returncode == 1, rejected
        assert "entry must be inside its root" in rejected.stderr, rejected

        if sys.platform != "win32":
            link = root / "linked.luc"
            link.symlink_to(outside)
            escaped_link = run("run", "--sandbox", str(root), str(link))
            assert escaped_link.returncode == 1, escaped_link
            assert "entry must be inside its root" in escaped_link.stderr, escaped_link

        missing = run("run", "--sandbox", str(root), str(root / "missing.luc"))
        assert missing.returncode == 1, missing
        assert "could not be resolved" in missing.stderr, missing

        malformed = run("run", "--sandbox", str(root))
        assert malformed.returncode == 2, malformed
        assert "luce run --sandbox ROOT FILE" in malformed.stdout, malformed

        good = run("run", "--sandbox", str(root), str(program), "--", "inside")
        unsupported_windows = (
            sys.platform == "win32"
            and good.returncode == 1
            and "not available on this host" in good.stderr
        )
        nested_macos = (
            sys.platform == "darwin"
            and good.returncode == 1
            and "Operation not permitted" in good.stderr
        )
        if unsupported_windows:
            assert good.stdout == "", good
            print("sandbox kernel run unavailable: Windows fails closed")
        elif nested_macos:
            # macOS refuses applying a second Seatbelt profile. This is expected under
            # sandboxed development runners; importantly, Luce failed closed. Unsandboxed
            # macOS CI exercises the successful kernel path.
            assert good.stdout == "", good
            print("sandbox kernel run skipped: enclosing macOS sandbox refuses nesting")
        else:
            assert good.returncode == 0, good
            assert good.stdout == "inside\n", good
            assert good.stderr == "", good

            helper = root / "helper.luc"
            helper.write_text(
                "pub func value() -> int:\n    return 0\n", encoding="utf-8"
            )
            program.write_text(
                "import helper\n\npub func main(arguments: list[str]) -> int!:\n    return helper.value()\n",
                encoding="utf-8",
            )
            local_import = run("run", "--sandbox", str(root), str(program))
            assert local_import.returncode == 0, local_import

            (root / "native.lucb").write_text(
                "pub func value() -> i32:\n    return 0\n", encoding="utf-8"
            )
            program.write_text(
                "import native\n\npub func main(arguments: list[str]) -> int!:\n    return 0\n",
                encoding="utf-8",
            )
            base_import = run("run", "--sandbox", str(root), str(program))
            assert base_import.returncode == 1, base_import
            assert "may not import Luce Base" in base_import.stderr, base_import

            dependency = parent / "dependency"
            dependency.mkdir()
            (dependency / "luce.toml").write_text(
                '[package]\nname = "dependency"\nsource = "src"\n\n'
                '[exports]\nsecret = "secret"\n',
                encoding="utf-8",
            )
            (dependency / "src").mkdir()
            (dependency / "src" / "secret.luc").write_text(
                "pub func value() -> int:\n    return 99\n", encoding="utf-8"
            )
            (root / "luce.toml").write_text(
                '[package]\nname = "root"\nsource = "."\n\n'
                '[dependencies]\ndependency = "../dependency"\n',
                encoding="utf-8",
            )
            program.write_text(
                "import secret\n\npub func main(arguments: list[str]) -> int!:\n    return secret.value()\n",
                encoding="utf-8",
            )
            escaped = run("run", "--sandbox", str(root), str(program))
            assert escaped.returncode != 0, escaped
            assert escaped.stdout == "", escaped

            (root / "luce.toml").unlink()
            program.write_text(
                "pub func main(arguments: list[str]) -> int!:\n"
                "    var i = 0\n"
                "    while i < 200000:\n"
                '        print("0123456789")\n'
                "        i += 1\n"
                "    return 0\n",
                encoding="utf-8",
            )
            flooded = run("run", "--sandbox", str(root), str(program))
            assert flooded.returncode == 1, flooded
            assert flooded.stdout == "", flooded
            assert "exceeded its output limit" in flooded.stderr, flooded

        policy = run("--sandbox-policy")
        assert policy.returncode == 0, policy
        assert policy.stdout == "luce-sandbox/1\n", policy

    print("sandbox ok")


if __name__ == "__main__":
    main()
