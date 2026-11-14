import os
from datetime import datetime

from bson.timestamp import Timestamp
from pymongo import MongoClient
from pymongo.errors import PyMongoError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27018")
DB_NAME = "cleanupDB"
SEPARATOR = "-" * 70

COLLECTIONS = {"1": "cleanupEvents", "2": "volunteers"}

ACTION_LABELS = {
    "1": "Display all documents",
    "2": "Add a new document",
    "3": "Update a document",
    "4": "Delete a document",
    "5": "Search documents",
    "6": "Exit system",
}


def ask_option(title, options):
    print(f"\n{title}")
    for key, label in options.items():
        print(f"  {key}. {label}")
    while True:
        choice = input("Your choice: ").strip()
        if choice in options:
            return choice
        print("Invalid choice, try again.")


def format_value(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, Timestamp):
        return format_value(value.as_datetime())
    if isinstance(value, dict):
        return ", ".join(f"{key}: {format_value(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " | ".join(format_value(item) for item in value) or "none"
    return str(value)


def print_document(document):
    print(SEPARATOR)
    for field, value in document.items():
        print(f"{field:<16}{format_value(value)}")


def display_all(collection):
    count = 0
    for document in collection.find():
        print_document(document)
        count += 1
    print(SEPARATOR)
    print(f"{count} document(s) in {collection.name}.")


def add_document(collection):
    print("Add is not available yet.")


def update_document(collection):
    print("Update is not available yet.")


def delete_document(collection):
    print("Delete is not available yet.")


def search_documents(collection):
    print("Search is not available yet.")


ACTIONS = {
    "1": display_all,
    "2": add_document,
    "3": update_document,
    "4": delete_document,
    "5": search_documents,
}


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except PyMongoError as error:
        print(f"Could not connect to MongoDB: {error}")
        return
    database = client[DB_NAME]
    while True:
        collection = database[COLLECTIONS[ask_option("Choose a collection", COLLECTIONS)]]
        action = ask_option(f"Choose an action on {collection.name}", ACTION_LABELS)
        if action == "6":
            break
        try:
            ACTIONS[action](collection)
        except PyMongoError as error:
            print(f"Database error: {error}")
    client.close()
    print("Goodbye.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
