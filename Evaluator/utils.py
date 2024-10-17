import ast

import numpy as np
import pandas as pd


def select_k_categories(df: pd.DataFrame, k, min_count=1, max_count=float('inf')):
    # Initialize an empty dictionary to count occurrences of each category
    category_counts = {}

    # Iterate through each row in the DataFrame
    for category_value in df['categories']:
        # Convert the category value to a list if it's a string representation of a list
        if isinstance(category_value, str):
            try:
                category_value = ast.literal_eval(category_value)
            except (ValueError, SyntaxError):
                category_value = [category_value]

        # Ensure category_value is a list
        if not isinstance(category_value, list):
            category_value = [category_value]

        # Count occurrences of each category
        for cat in category_value:
            cat = str(cat).strip().lower()
            if cat not in category_counts:
                category_counts[cat] = 0
            category_counts[cat] += 1

    # Filter categories based on the min and max count thresholds
    filtered_categories = [cat for cat, count in category_counts.items()
                           if min_count <= count <= max_count]

    if len(filtered_categories) < k:
        print(f"changing number of tests to max possible k={len(filtered_categories)}")
        k = len(filtered_categories)
        # raise ValueError(f"Not enough categories meet the criteria to select {k}, num available categories {len(filtered_categories)}.")

    # Randomly sample k categories
    return np.random.choice(filtered_categories, k, replace=False).tolist(), category_counts


def check_category(df, filename, target_category: str):
    # Step 1: Find the row with the given filename
    row = df[df['filename'] == filename]

    # Step 2: Check if the row exists
    if row.empty:
        print(f"{filename} not found")
        return False

    # Get the category value from the row
    category_value = row['categories'].values[0]

    # Convert the category value to a Python list if it's a string representation of a list
    if isinstance(category_value, str):
        try:
            category_value = ast.literal_eval(category_value)
        except (ValueError, SyntaxError):
            # If conversion fails, treat it as a single category
            category_value = [category_value]

    # Ensure category_value is a list
    if not isinstance(category_value, list):
        category_value = [category_value]

    # Step 3: Check if the target_category is in the list of categories
    return target_category.lower().strip() in [cat.lower().strip() for cat in category_value]

def get_category_counts(df):
    # Initialize an empty dictionary to count occurrences of each category
    category_counts = {}

    # Iterate through each row in the DataFrame
    for category_value in df['categories']:
        # Convert the category value to a list if it's a string representation of a list
        if isinstance(category_value, str):
            try:
                category_value = ast.literal_eval(category_value)
            except (ValueError, SyntaxError):
                category_value = [category_value]

        # Ensure category_value is a list
        if not isinstance(category_value, list):
            category_value = [category_value]

        # Count occurrences of each category
        for cat in category_value:
            cat = str(cat).strip().lower()
            if cat not in category_counts:
                category_counts[cat] = 0
            category_counts[cat] += 1

        return category_counts