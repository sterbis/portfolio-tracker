from pathlib import Path


def print_directory_structure() -> None:
    for root_path, _, file_names in Path(
        r"src\portfolio_tracker\application"
    ).walk():
        if root_path.name.startswith("__"):
            continue

        print(root_path)
        for file_name in file_names:
            print(root_path / file_name)


print_directory_structure()
