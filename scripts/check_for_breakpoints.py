import re
import sys

BREAKPOINT_PATTERNS = [
    r"breakpoint\(\)",
    r"pdb\.set_trace\(\)",
    r"import pdb",
    r"from pdb import",
    r"ipdb\.set_trace\(\)",
    r"import ipdb",
    r"from ipdb import",
]


def check_file(filename: str) -> list[str]:
    with open(filename, "r") as f:
        content = f.read()

    found_breakpoints: list[str] = []
    for pattern in BREAKPOINT_PATTERNS:
        matches = re.findall(pattern, content)
        for match in matches:
            found_breakpoints.append(f"{filename}: {match}")

    return found_breakpoints


if __name__ == "__main__":
    files = sys.argv[1:]
    all_breakpoints: list[str] = []

    for file in files:
        breakpoints = check_file(file)
        all_breakpoints.extend(breakpoints)

    if all_breakpoints:
        print("Found breakpoints in files:")
        for bp in all_breakpoints:
            print(f"  {bp}")
        sys.exit(1)

    sys.exit(0)
