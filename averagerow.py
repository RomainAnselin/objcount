import os
import sys

def calculate_row_sizes(filename):
    row_count = 0
    row_sizes = []
    with open(filename, 'r') as file:
        for line in file:
            row_count += 1
            row_size = len(line.encode('utf-8'))  # Get the size of the line in bytes
            row_sizes.append(row_size)

    return row_sizes, row_count

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <filename>")
        return

    filename = sys.argv[1]
    if not os.path.exists(filename):
        print("File not found.")
        return

    row_sizes, row_count = calculate_row_sizes(filename)

    if row_sizes:
        average_size = sum(row_sizes) / len(row_sizes)
        max_size = max(row_sizes)
        min_size = min(row_sizes)

        print("Number of rows:", row_count)
        print("Average row size:", average_size)
        print("Max row size:", max_size)
        print("Min row size:", min_size)
    else:
        print("No rows found in the file.")

if __name__ == "__main__":
    main()
