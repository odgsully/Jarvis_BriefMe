import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description="Process a transcript file.")
    parser.add_argument('transcript_file', type=str, help='The path to the transcript file')
    parser.add_argument('--min_count_threshold', type=int, default=3, help='Minimum count threshold for word frequency display')
    return parser.parse_args()
