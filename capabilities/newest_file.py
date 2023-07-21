import os
import argparse
import sys

def newest_files_in_dir(directory, n=1, exclude=[]):
    all_files = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not any(excluded_dir in os.path.join(root, d) for excluded_dir in exclude)]
        for file in files:
            full_path = os.path.join(root, file)
            timestamp = os.path.getmtime(full_path)
            all_files.append((full_path, timestamp))

    sorted_files = sorted(all_files, key=lambda x: x[1], reverse=True)
    return [file[0] for file in sorted_files[:n]]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', help='Directory to search')
    parser.add_argument('n', nargs='?', default=1, type=int, help='Number of files to return')
    parser.add_argument('--exclude', nargs='*', default=[], help='List of directories to exclude')
    args = parser.parse_args()

    for file in newest_files_in_dir(args.directory, args.n, args.exclude):
        print(file)
