import math
from collections import Counter, defaultdict

import pytest

from conftest import QUERIES, run_query


def names(documents):
    return [document["name"] for document in documents]


def distance_m(a, b):
    """Haversine distance in metres between two [longitude, latitude] points."""
    lon1, lat1, lon2, lat2 = map(math.radians, [*a, *b])
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6378100 * math.asin(math.sqrt(h))


def test_the_script_contains_15_queries():
    assert sorted(QUERIES) == list(range(1, 16))


def test_query_01_completed_events(db):
    expected = names(db.cleanupEvents.find({"status": "completed"}))
    result = run_query(1)
    assert len(result) == 8
    assert sorted(names(result)) == sorted(expected)


def test_query_02_volunteer_by_email(db):
    result = run_query(2)
    assert result == {
        "name": "Emma Walsh",
        "email": "emmawalsh123@example.com",
        "skills": ["first aid", "languages"],
        "hoursLogged": 10,
    }


def test_query_03_sponsored_events(db):
    result = run_query(3)
    assert result and all(event["sponsored"] for event in result)
    assert len(result) == db.cleanupEvents.count_documents({"sponsored": True})


def test_query_04_completed_events_newest_first(db):
    result = run_query(4)
    dates = [event["date"] for event in result]
    assert all(event["status"] == "completed" for event in result)
    assert dates == sorted(dates, reverse=True)


def test_query_05_top_five_volunteers_by_hours(db):
    hours = sorted((v["hoursLogged"] for v in db.volunteers.find()), reverse=True)[:5]
    result = run_query(5)
    assert [volunteer["hoursLogged"] for volunteer in result] == hours
    assert all(set(volunteer) == {"name", "hoursLogged"} for volunteer in result)


def test_query_06_drivers_or_first_aiders(db):
    expected = {v["name"] for v in db.volunteers.find() if {"driving", "first aid"} & set(v["skills"])}
    assert set(names(run_query(6))) == expected


def test_query_07_volunteers_with_both_badges(db):
    expected = {v["name"] for v in db.volunteers.find() if {"First Cleanup", "10 Hours"} <= set(v["badges"])}
    assert set(names(run_query(7))) == expected == {"Emma Walsh", "Arjun Sharma"}


def test_query_08_volunteers_with_three_skills(db):
    assert names(run_query(8)) == ["Alice Wang"]


def test_query_09_events_with_20kg_of_plastic(db):
    expected = {
        e["name"] for e in db.cleanupEvents.find()
        if any(w["type"] == "plastic" and w["weightKg"] >= 20 for w in e["wasteCollected"])
    }
    assert set(names(run_query(9))) == expected == {"Grand Canal Clean-up", "Dollymount Beach Clean"}


def test_query_10_events_within_2km_closest_first(db):
    centre = [-6.2603, 53.3498]
    distances = {e["name"]: distance_m(centre, e["location"]["coordinates"]) for e in db.cleanupEvents.find()}
    expected = sorted((name for name, d in distances.items() if d <= 2000), key=distances.get)
    assert names(run_query(10)) == expected
    assert expected, "no event is within 2 km, the query proves nothing"


def test_query_11_total_weight_per_waste_type(db):
    totals = defaultdict(float)
    for event in db.cleanupEvents.find({"status": "completed"}):
        for waste in event["wasteCollected"]:
            totals[waste["type"]] += waste["weightKg"]
    result = run_query(11)
    assert {row["_id"]: row["totalKg"] for row in result} == pytest.approx(dict(totals))
    assert [row["totalKg"] for row in result] == sorted(totals.values(), reverse=True)


def test_query_12_busiest_zones(db):
    counts = Counter(event["zone"] for event in db.cleanupEvents.find())
    result = run_query(12)
    assert len(result) == 5
    assert all(row["eventCount"] == counts[row["_id"]] for row in result)
    assert [row["eventCount"] for row in result] == sorted(counts.values(), reverse=True)[:5]


def test_query_13_events_with_few_volunteers(db):
    expected = {
        e["name"] for e in db.cleanupEvents.find()
        if e["status"] != "cancelled" and len(e["volunteers"]) <= 3
    }
    result = run_query(13)
    assert set(names(result)) == expected
    counts = [row["volunteerCount"] for row in result]
    assert counts == sorted(counts)


def test_query_14_most_active_volunteers(db):
    result = run_query(14)
    assert len(result) == 5
    for row in result:
        volunteer = db.volunteers.find_one({"_id": row["_id"]})
        assert row["eventsCount"] == len(volunteer["eventsAttended"])
        assert row["totalHours"] == pytest.approx(volunteer["hoursLogged"])


def test_query_15_sponsored_against_not_sponsored(db):
    weights = defaultdict(list)
    for event in db.cleanupEvents.find({"status": "completed"}):
        weights[event["sponsored"]].append(sum(w["weightKg"] for w in event["wasteCollected"]))
    result = {row["sponsored"]: row for row in run_query(15)}
    for sponsored, values in weights.items():
        assert result[sponsored]["eventCount"] == len(values)
        assert result[sponsored]["avgWeightPerEventKg"] == pytest.approx(sum(values) / len(values))
