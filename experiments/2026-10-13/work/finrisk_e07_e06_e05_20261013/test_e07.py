import unittest
try:
    from e07 import validate_input_record
except ImportError:
    validate_input_record = None


class E07Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(validate_input_record, "E07 implementation not present")
        self.record = {"query_id": "X", "text": "尚不清楚是否回流，未授权。", "conditions": [
            {"field_id": "flow", "state": "unknown", "quote": "尚不清楚是否回流"},
            {"field_id": "auth", "state": "absent", "quote": "未授权"}]}

    def test_unknown_retained_and_targeted(self):
        self.assertEqual(validate_input_record(self.record, {"flow", "auth"}), ["flow"])

    def test_false_is_not_unknown_state(self):
        self.record["conditions"][0]["state"] = False
        with self.assertRaises(ValueError):
            validate_input_record(self.record, {"flow", "auth"})

    def test_invented_input_quote_rejected(self):
        self.record["conditions"][1]["quote"] = "已授权"
        with self.assertRaises(ValueError):
            validate_input_record(self.record, {"flow", "auth"})

    def test_no_extra_benefit_suppresses_dependent_questions(self):
        from e07 import followup_fields
        record = {"mechanism_id": "extra_benefit", "conditions": [
            {"field_id": "extra_benefit_claimed", "state": "absent", "quote": "无额外利益"},
            {"field_id": "purchase_link_stated", "state": "unknown", "quote": ""},
            {"field_id": "delivery_known", "state": "unknown", "quote": ""}]}
        self.assertEqual(followup_fields(record), [])

if __name__ == "__main__":
    unittest.main()
