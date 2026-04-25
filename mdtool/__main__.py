import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mdtool",
        description="파일을 Markdown으로 변환합니다 (PPTX 등).",
    )
    parser.add_argument("input", nargs="?", help="변환할 파일 경로 (생략 시 GUI 실행)")
    parser.add_argument("-o", "--output", help="저장할 .md 경로 (생략 시 stdout)")
    parser.add_argument("--gui", action="store_true", help="GUI 실행")
    args = parser.parse_args()

    if args.gui or not args.input:
        from .app import main as gui_main

        gui_main()
        return

    from .converters import convert_file

    md = convert_file(Path(args.input))
    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
    else:
        sys.stdout.write(md)


if __name__ == "__main__":
    main()
