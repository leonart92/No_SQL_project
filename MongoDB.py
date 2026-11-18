import os
import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.timestamp import Timestamp
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError, WriteError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "cleanupDB"
SEPARATOR = "-" * 70
DATE_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d")
WASTE_TYPES = ["plastic", "glass", "paper", "metal", "organic", "electronics"]
STATUSES = ["planned", "completed", "cancelled"]

COLLECTIONS = {"1": "cleanupEvents", "2": "volunteers"}

REFERENCES = {
    "cleanupEvents": ("volunteers", "eventsAttended"),
    "volunteers": ("cleanupEvents", "volunteers"),
}

SEARCH_FIELDS = {
    "cleanupEvents": ["name", "zone", "status", "organiser.name", "wasteCollected.type"],
    "volunteers": ["name", "email", "address.city", "skills", "badges"],
}

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


def print_documents(documents):
    count = 0
    for document in documents:
        print_document(document)
        count += 1
    print(SEPARATOR)
    return count


def display_all(collection):
    count = print_documents(collection.find())
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


def ask_choice(label, values):
    while True:
        value = input(f"{label} ({', '.join(values)}): ").strip().lower()
        if value in values:
            return value
        print("Please pick one of the listed values.")


def ask_waste_collected():
    waste = []
    while ask_yes_no("Add a waste entry"):
        waste.append({
            "type": ask_choice("Waste type", WASTE_TYPES),
            "weightKg": ask_number("Weight in kg", minimum=0),
        })
    return waste


def current_timestamp():
    return Timestamp(datetime.now(timezone.utc), 1)


def ask_location():
    return {
        "type": "Point",
        "coordinates": [
            ask_number("Longitude", -180, 180),
            ask_number("Latitude", -90, 90),
        ],
    }


def ask_organiser():
    return {
        "name": ask_text("Organiser name"),
        "email": ask_email("Organiser email"),
        "phone": ask_text("Organiser phone"),
    }


def ask_address():
    return {
        "street": ask_text("Street"),
        "city": ask_text("City"),
        "eircode": ask_text("Eircode"),
    }


FIELD_INPUTS = {
    "cleanupEvents": {
        "name": lambda database: ask_text("Name"),
        "date": lambda database: ask_date("Date"),
        "zone": lambda database: ask_text("Zone"),
        "location": lambda database: ask_location(),
        "organiser": lambda database: ask_organiser(),
        "volunteers": lambda database: ask_references("Volunteer ids", database["volunteers"]),
        "wasteCollected": lambda database: ask_waste_collected(),
        "durationHours": lambda database: ask_number("Duration in hours", minimum=0),
        "sponsored": lambda database: ask_yes_no("Sponsored"),
        "status": lambda database: ask_choice("Status", STATUSES),
    },
    "volunteers": {
        "name": lambda database: ask_text("Full name"),
        "email": lambda database: ask_email("Email"),
        "address": lambda database: ask_address(),
        "skills": lambda database: ask_list("Skills"),
        "hoursLogged": lambda database: ask_number("Hours logged", minimum=0),
        "badges": lambda database: ask_list("Badges"),
        "hasEquipment": lambda database: ask_yes_no("Has own equipment"),
        "joinedAt": lambda database: ask_date("Joined on"),
        "eventsAttended": lambda database: ask_references("Attended event ids", database["cleanupEvents"]),
    },
}


def add_document(collection):
    inputs = FIELD_INPUTS[collection.name]
    document = {field: ask_value(collection.database) for field, ask_value in inputs.items()}
    document["lastUpdated"] = current_timestamp()
    result = collection.insert_one(document)
    print(f"Document added with id {result.inserted_id}.")


def find_by_id(collection):
    value = ask_text("Document id")
    if not ObjectId.is_valid(value):
        print("An id must be a 24 character hexadecimal string.")
        return None
    document = collection.find_one({"_id": ObjectId(value)})
    if document is None:
        print(f"No document with this id in {collection.name}.")
    return document


def update_document(collection):
    document = find_by_id(collection)
    if document is None:
        return
    print_document(document)
    inputs = FIELD_INPUTS[collection.name]
    fields = {str(number): field for number, field in enumerate(inputs, start=1)}
    field = fields[ask_option("Choose the field to update", fields)]
    value = inputs[field](collection.database)
    collection.update_one(
        {"_id": document["_id"]},
        {"$set": {field: value, "lastUpdated": current_timestamp()}},
    )
    print(f"Field {field} updated.")


def delete_document(collection):
    document = find_by_id(collection)
    if document is None:
        return
    print_document(document)
    if not ask_yes_no("Delete this document"):
        print("Nothing was deleted.")
        return
    collection.delete_one({"_id": document["_id"]})
    linked_collection, field = REFERENCES[collection.name]
    collection.database[linked_collection].update_many(
        {field: document["_id"]},
        {"$pull": {field: document["_id"]}, "$set": {"lastUpdated": current_timestamp()}},
    )
    print("Document deleted.")


def search_documents(collection):
    keyword = ask_text("Keyword")
    pattern = {"$regex": re.escape(keyword), "$options": "i"}
    query = {"$or": [{field: pattern} for field in SEARCH_FIELDS[collection.name]]}
    count = print_documents(collection.find(query))
    print(f"{count} document(s) matching '{keyword}' in {collection.name}.")


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
        except DuplicateKeyError:
            print("A volunteer with this email already exists.")
        except WriteError as error:
            print(f"The database rejected the change: {error.details.get('errmsg', error)}")
        except PyMongoError as error:
            print(f"Database error: {error}")
    client.close()
    print("Goodbye.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
