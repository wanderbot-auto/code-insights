from __future__ import annotations

import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def step(title: str) -> None:
    print(f"[replay] {title}")


def main() -> None:
    app = ROOT / "app.py"
    utils = ROOT / "utils.py"
    web = ROOT / "web.js"
    new_file = ROOT / "new_feature.py"

    step("wait 1s")
    time.sleep(1)

    step("modify app.py (+comment +code)")
    app.write_text(app.read_text(encoding="utf-8") + "\n# replay_step_1\nreplay_value = 7\n", encoding="utf-8")

    step("wait 1s")
    time.sleep(1)

    step("append comment to utils.py")
    utils.write_text(utils.read_text(encoding="utf-8") + "\n# replay_step_2\n", encoding="utf-8")

    step("wait 1s")
    time.sleep(1)

    step("add new_feature.py")
    new_file.write_text("def generated():\n    return 'ok'\n", encoding="utf-8")

    step("wait 1s")
    time.sleep(1)

    if web.exists():
        step("delete web.js")
        web.unlink()
    else:
        step("web.js already deleted; skip")

    step("done")


if __name__ == "__main__":
    main()
