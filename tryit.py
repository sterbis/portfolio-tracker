from pathlib import Path


def print_directory_structure(root_path: str | Path) -> None:
    root_path = Path(root_path)
    for dir_path, _, file_names in root_path.walk():
        if dir_path.name.startswith("__"):
            continue

        print(dir_path.relative_to(root_path.parent))
        for file_name in file_names:
            path = dir_path / file_name
            print(path.relative_to(root_path.parent))


print_directory_structure(r"src\portfolio_tracker\domain")
