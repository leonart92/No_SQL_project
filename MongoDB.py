import os

from pymongo import MongoClient
from pymongo.errors import PyMongoError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27018")
DB_NAME = "cleanupDB"

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


def display_all(collection):
    print("Display is not available yet.")


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
