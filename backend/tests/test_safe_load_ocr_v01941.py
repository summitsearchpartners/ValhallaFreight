from app.services.safe_load_images import _expiry_label_date, _supplement_front


def test_expiration_on_separate_ocr_line():
    text = "4a ISS 05/11/2026\n4b EXP\n03/31/2030\n3 DOB 03/30/1984"
    assert _expiry_label_date(text) == "03312030"


def test_expiration_on_same_ocr_line():
    assert _expiry_label_date("4bEXP 03/31/2030") == "03312030"


def test_dob_not_used_as_expiration():
    assert _expiry_label_date("DOB 03/30/1984\nISS 05/11/2026") == ""


def test_neural_observation_can_fill_missing_expiry():
    assert _supplement_front({}, "4bEXP 03/31/2030")["DBA"] == "03312030"
