"""Battle picks must never silently swap letter identities or approve flawed references."""
import json
import pytest
from skell_sound_match.wav_only.battle_feedback import validate_and_plan, to_markdown, main


def sample():
    return {"schema":"skelly.sound-battle-feedback.v1","session_id":"s1","results":[
        {"group_id":"deuce-main-r5", "preset":"Deuce", "winner":"C", "eliminate":"A",
         "notes":"original lacked FX", "survivors":["b", "c"],
         "candidate_versions":[{"letter":"A","identity":"a"},{"letter":"B","identity":"b"},{"letter":"C","identity":"c"}]},
        {"group_id":"angelic", "preset":"Angelic", "winner":"tie", "eliminate":"",
         "notes":"incomplete", "survivors":["a1","b1","c1"],
         "candidate_versions":[{"letter":"A","identity":"a1"},{"letter":"B","identity":"b1"},{"letter":"C","identity":"c1"}]},
        {"group_id":"alchemist", "preset":"Alchemist", "winner":"tie", "eliminate":"A",
         "notes":"", "survivors":["b2", "c2"],
         "candidate_versions":[{"letter":"A","identity":"a2"},{"letter":"B","identity":"b2"},{"letter":"C","identity":"c2"}]},
    ]}


def test_resolves_provisional_and_blocks_bad_reference():
    plan=validate_and_plan(sample(), {"deuce-main-r5"})
    assert plan["summary"] == {"groups":3,"provisional_winners":0,"reference_repair":1,"ties":2,"ready_for_challenger":1}
    assert plan["groups"][0]["winner_identity"] == "c"
    assert plan["groups"][0]["queue_state"] == "repair_reference_first"
    assert plan["groups"][0]["listening_approved"] is False


def test_tie_keeps_all_when_no_elimination():
    g=validate_and_plan(sample())["groups"][1]
    assert len(g["survivors"]) == 3
    assert g["queue_state"] == "refine_before_next_vote"
    assert g["eliminated_identity"] is None


def test_tie_with_elimination_keeps_exact_two():
    g=validate_and_plan(sample())["groups"][2]
    assert g["winner_identity"] is None
    assert g["survivors"] == ["b2","c2"]
    assert g["queue_state"] == "ready_for_challenger"


def test_unknown_group_reference_flag_rejected():
    with pytest.raises(ValueError,match="does not match"):
        validate_and_plan(sample(), {"someone-else"})


def test_candidate_survivor_consistency_rejected():
    x=sample();x["results"][0]["survivors"]=["b","a"]
    with pytest.raises(ValueError,match="Survivor list"):
        validate_and_plan(x)


def test_winner_cannot_be_eliminated():
    x=sample();x["results"][0]["eliminate"]="C"
    with pytest.raises(ValueError,match="Winner cannot"):
        validate_and_plan(x)


def test_duplicate_ids_and_letters_rejected():
    x=sample();x["results"].append(dict(x["results"][0]))
    with pytest.raises(ValueError,match="Duplicate group"):
        validate_and_plan(x)
    x=sample();x["results"][0]["candidate_versions"][1]["letter"]="A"
    with pytest.raises(ValueError,match="duplicate candidate letter"):
        validate_and_plan(x)


def test_unrecognized_schema_rejected():
    x=sample();x["schema"]="random"
    with pytest.raises(ValueError,match="schema"):
        validate_and_plan(x)


def test_notes_escaped_in_public_md():
    x=sample();x["results"][0]["notes"]="tone | character\nmissing"
    m=to_markdown(validate_and_plan(x))
    assert "tone \\| character missing" in m


def test_cli_creates_two_files_and_refuses_overwrite(tmp_path):
    src=tmp_path/"picks.json";src.write_text(json.dumps(sample()))
    out=tmp_path/"plans"
    assert main([str(src),"--output-dir",str(out),"--reference-issue","deuce-main-r5"]) == 0
    a=json.loads((out/"BATTLE_NEXT_ROUND_PLAN.json").read_text())
    assert a["groups"][0]["queue_state"] == "repair_reference_first"
    with pytest.raises(SystemExit):
        main([str(src),"--output-dir",str(out)])
