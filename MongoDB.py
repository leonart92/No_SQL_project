import os
import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.timestamp import Timestamp
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError, WriteError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27018")
DB_NAME = "cleanupDB"
SEPARATOR = "-" * 70
DATE_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d")

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


def ask_text(label):
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print("This field is required.")


def ask_email(label):
    while True:
        value = ask_text(label)
        if re.fullmatch(r".+@.+\..+", value):
            return value
        print("Please enter a valid email address.")


def ask_number(label, minimum=float("-inf"), maximum=float("inf")):
    while True:
        try:
            value = float(input(f"{label}: "))
        except ValueError:
            print("Please enter a number.")
            continue
        if minimum <= value <= maximum:
            return value
        print("This value is out of range.")


def ask_yes_no(label):
    while True:
        answer = input(f"{label} (y/n): ").strip().lower()
        if answer in ("y", "n"):
            return answer == "y"
        print("Please answer y or n.")


def ask_date(label):
    while True:
        text = input(f"{label} (YYYY-MM-DD or YYYY-MM-DD HH:MM): ").strip()
        for date_format in DATE_FORMATS:
            try:
                return datetime.strptime(text, date_format)
            except ValueError:
                continue
        print("Please enter a valid date.")


def ask_list(label):
    text = input(f"{label} (comma separated, empty for none): ")
    return [item.strip() for item in text.split(",") if item.strip()]


def ask_references(label, target_collection):
    while True:
        values = ask_list(label)
        if not all(ObjectId.is_valid(value) for value in values):
            print("Each id must be a 24 character hexadecimal string.")
            continue
        ids = [ObjectId(value) for value in values]
        found = target_collection.count_documents({"_id": {"$in": ids}})
        if found == len(set(ids)):
            return ids
        print(f"Some ids do not exist in {target_collection.name}.")


def current_timestamp():
    return Timestamp(datetime.now(timezone.utc), 1)


def build_volunteer(database):
    return {
        "name": ask_text("Full name"),
        "email": ask_email("Email"),
        "address": {
            "street": ask_text("Street"),
            "city": ask_text("City"),
            "eircode": ask_text("Eircode"),
        },
        "skills": ask_list("Skills"),
        "hoursLogged": ask_number("Hours logged", minimum=0),
        "badges": ask_list("Badges"),
        "hasEquipment": ask_yes_no("Has own equipment"),
        "joinedAt": ask_date("Joined on"),
        "eventsAttended": ask_references("Attended event ids", database["cleanupEvents"]),
        "lastUpdated": current_timestamp(),
    }


BUILDERS = {"volunteers": build_volunteer}


def add_document(collection):
    if collection.name not in BUILDERS:
        print("Add is not available yet for this collection.")
        return
    document = BUILDERS[collection.name](collection.database)
    try:
        result = collection.insert_one(document)
    except DuplicateKeyError:
        print("A volunteer with this email already exists.")
    except WriteError as error:
        print(f"The document was rejected: {error.details.get('errmsg', error)}")
    else:
        print(f"Document added with id {result.inserted_id}.")


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
