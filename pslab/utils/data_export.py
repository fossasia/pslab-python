import csv
import json
import io

def export_to_csv(data, target, fieldnames=None):
    """
    Exports a list of dictionaries to a CSV file or file-like object.
    """
    if not data:
        raise ValueError("No data provided for export.")

    # Determine if target is a path (str) or a file-like object
    is_path = isinstance(target, str)
    f = open(target, "w", newline="", encoding="utf-8") if is_path else target

    try:
        writer = csv.DictWriter(f, fieldnames=fieldnames or data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    finally:
        if is_path:
            f.close()

def export_to_json(data, target):
    """
    Exports data to a JSON file or file-like object.
    """
    if not data:
        raise ValueError("No data provided for export.")

    is_path = isinstance(target, str)
    f = open(target, "w", encoding="utf-8") if is_path else target

    try:
        json.dump(data, f, indent=4)
    finally:
        if is_path:
            f.close()
