from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    print(read_text(Path(__file__)))


if __name__ == "__main__":
    main()

# monitor_round_1
value = 1

# replay_step_1
replay_value = 7
