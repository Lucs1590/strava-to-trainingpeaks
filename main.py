import os
import re
import questionary


def main():
    sport = questionary.select(
        "What sport do you want to export to trainingpeaks?",
        choices=[
            "Bike",
            "Run",
            "Swim",
            "Other",
        ],
    ).ask()

if __name__ == "__main__":
    main()
