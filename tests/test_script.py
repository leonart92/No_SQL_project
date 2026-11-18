from datetime import datetime, timezone

import pytest
from bson.timestamp import Timestamp
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, WriteError

from conftest import DB_NAME, MONGO_URI, run_script


def valid_event():
    return {
        "name": "Test Cleanup",
        "date": datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc),
        "zone": "Dublin 1",
        "location": {"type": "Point", "coordinates": [-6.26, 53.35]},
        "organiser": {"name": "Test Person", "email": "test@example.ie", "phone": "0870000000"},
        "volunteers": [],
        "wasteCollected": [],
        "durationHours": 2.0,
        "sponsored": False,
        "status": "planned",
        "lastUpdated": Timestamp(datetime.now(timezone.utc), 1),
    }


def valid_volunteer():
    return {
        "name": "Test Volunteer",
        "email": "new.volunteer@example.com",
        "address": {"street": "1 Test Street", "city": "Dublin", "eircode": "D01 TEST"},
        "skills": [],
        "hoursLogged": 0.0,
        "badges": [],
        "hasEquipment": False,
        "joinedAt": datetime(2026, 11, 1, tzinfo=timezone.utc),
        "eventsAttended": [],
        "lastUpdated": Timestamp(datetime.now(timezone.utc), 1),
    }


def test_script_runs_on_a_brand_new_server(client):
    # Same state as a new server: no database, no user, no role.
    database = client[DB_NAME]
    database.command("dropAllUsersFromDatabase")
    database.command("dropAllRolesFromDatabase")
    client.drop_database(DB_NAME)

    process = run_script()

    assert process.returncode == 0, process.stderr
    assert database.command("usersInfo", "Admin")["users"], "the Admin user was not created"


def test_script_can_run_twice_without_duplicates(client):
    for _ in range(2):
        process = run_script()
        assert process.returncode == 0, process.stderr
    database = client[DB_NAME]
    assert database.volunteers.count_documents({}) == 10
    assert database.cleanupEvents.count_documents({}) == 10


def test_at_least_ten_documents_per_collection(db):
    assert db.volunteers.count_documents({}) >= 10
    assert db.cleanupEvents.count_documents({}) >= 10


def test_a_valid_event_is_accepted(db):
    db.cleanupEvents.insert_one(valid_event())


def test_a_valid_volunteer_is_accepted(db):
    db.volunteers.insert_one(valid_volunteer())


@pytest.mark.parametrize("field", ["name", "date", "zone", "location", "status"])
def test_an_event_without_a_required_field_is_refused(db, field):
    event = valid_event()
    del event[field]
    with pytest.raises(WriteError):
        db.cleanupEvents.insert_one(event)


@pytest.mark.parametrize(
    "field, bad_value",
    [
        ("status", "finished"),
        ("sponsored", "yes"),
        ("durationHours", -1.0),
        ("wasteCollected", [{"type": "wood", "weightKg": 3.0}]),
        ("wasteCollected", [{"type": "plastic", "weightKg": -2.0}]),
        ("location", {"type": "Polygon", "coordinates": [-6.26, 53.35]}),
    ],
)
def test_an_event_with_a_wrong_value_is_refused(db, field, bad_value):
    event = valid_event()
    event[field] = bad_value
    with pytest.raises(WriteError):
        db.cleanupEvents.insert_one(event)


@pytest.mark.parametrize(
    "field, bad_value",
    [
        ("email", "not-an-email"),
        ("hoursLogged", -3.0),
        ("hasEquipment", "true"),
        ("skills", "first aid"),
        ("eventsAttended", ["65f00000000000000000b201"]),
    ],
)
def test_a_volunteer_with_a_wrong_value_is_refused(db, field, bad_value):
    volunteer = valid_volunteer()
    volunteer[field] = bad_value
    with pytest.raises(WriteError):
        db.volunteers.insert_one(volunteer)


def test_two_volunteers_cannot_share_an_email(db):
    volunteer = valid_volunteer()
    volunteer["email"] = "emmawalsh123@example.com"
    with pytest.raises(DuplicateKeyError):
        db.volunteers.insert_one(volunteer)


def test_location_has_a_2dsphere_index(db):
    keys = [index["key"] for index in db.cleanupEvents.list_indexes()]
    assert {"location": "2dsphere"} in [dict(key) for key in keys]


def test_email_index_is_unique(db):
    indexes = {index["name"]: index for index in db.volunteers.list_indexes()}
    assert indexes["email_1"].get("unique") is True


def test_every_reference_points_to_an_existing_document(db):
    event_ids = {event["_id"] for event in db.cleanupEvents.find({}, {"_id": 1})}
    volunteer_ids = {volunteer["_id"] for volunteer in db.volunteers.find({}, {"_id": 1})}
    for volunteer in db.volunteers.find():
        assert set(volunteer["eventsAttended"]) <= event_ids, volunteer["name"]
    for event in db.cleanupEvents.find():
        assert set(event["volunteers"]) <= volunteer_ids, event["name"]


def test_events_and_volunteers_reference_each_other(db):
    events = {event["_id"]: event for event in db.cleanupEvents.find()}
    for volunteer in db.volunteers.find():
        for event_id in volunteer["eventsAttended"]:
            assert events[event_id]["status"] == "completed", volunteer["name"]
            assert volunteer["_id"] in events[event_id]["volunteers"], volunteer["name"]
    for event in events.values():
        if event["status"] == "completed":
            for volunteer_id in event["volunteers"]:
                volunteer = db.volunteers.find_one({"_id": volunteer_id})
                assert event["_id"] in volunteer["eventsAttended"], event["name"]


def test_hours_logged_match_the_events_attended(db):
    durations = {event["_id"]: event["durationHours"] for event in db.cleanupEvents.find()}
    for volunteer in db.volunteers.find():
        expected = sum(durations[event_id] for event_id in volunteer["eventsAttended"])
        assert volunteer["hoursLogged"] == pytest.approx(expected), volunteer["name"]


def test_admin_role_has_crud_rights_on_both_collections(db):
    role = db.command("rolesInfo", "adminRole", showPrivileges=True)["roles"][0]
    rights = {privilege["resource"]["collection"]: set(privilege["actions"]) for privilege in role["privileges"]}
    crud = {"find", "insert", "update", "remove"}
    assert rights == {"cleanupEvents": crud, "volunteers": crud}


def test_admin_user_has_the_admin_role(db):
    user = db.command("usersInfo", "Admin")["users"][0]
    assert {"role": "adminRole", "db": DB_NAME} in user["roles"]


def test_admin_can_log_in_with_its_password(db):
    admin = MongoClient(MONGO_URI, username="Admin", password="pa33word", authSource=DB_NAME,
                        serverSelectionTimeoutMS=3000)
    try:
        assert admin[DB_NAME].volunteers.count_documents({}) == 10
    finally:
        admin.close()
