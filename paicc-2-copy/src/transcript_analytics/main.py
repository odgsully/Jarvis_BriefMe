from .arg_parse import parse_arguments
from dotenv import load_dotenv
from .constants import word_blacklist
from .llm import analyze_transcript

load_dotenv()


def main():
    args = parse_arguments()
    transcript_file = args.transcript_file
    min_count_threshold = args.min_count_threshold

    with open(transcript_file, "r") as file:
        transcript_content = file.read()

        # Count the frequency of each word
        word_count = {}
        for word in transcript_content.split():
            word = word.lower()  # Convert to lowercase to ensure case-insensitivity
            if word in word_blacklist:
                continue
            if word in word_count:
                word_count[word] += 1
            else:
                word_count[word] = 1

        # Display the word frequencies sorted by count in descending order
        print("\nWord Frequencies:")
        for word, count in sorted(
            word_count.items(), key=lambda item: item[1], reverse=True
        ):
            if count > min_count_threshold:
                print(f"{word} ({count}): {'#' * count}")

        # Analyze the transcript and print the results
        analysis = analyze_transcript(transcript_content, word_count)
        print("\nTranscript Analysis:")
        print(f"Quick Summary: {analysis.quick_summary}")
        print("Bullet Point Highlights:")
        for highlight in analysis.bullet_point_highlights:
            print(f"- {highlight}")
        print(f"Sentiment Analysis: {analysis.sentiment_analysis}")
        print("Keywords:")
        for keyword in analysis.keywords:
            print(f"- {keyword}")


if __name__ == "__main__":
    main()
