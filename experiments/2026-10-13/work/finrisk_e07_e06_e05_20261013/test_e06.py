import unittest
import copy
try:
    import e06
except ImportError:
    e06 = None


class E06Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(e06, "E06 implementation absent")
        self.graph = {"events": [{"event_id": "ev", "status": "source_supported", "members": [
            {"file_id": "F1", "source_sha256": "abc", "event_spans": [{"start": 10, "end": 30}], "role": "institution_behavior"},
            {"file_id": "F2", "source_sha256": "def", "event_spans": [{"start": 0, "end": 20}], "role": "management_responsibility"}]}]}
        self.units = {"u1": {"file_id": "F1", "source_sha256": "abc", "source_spans": [{"start": 12, "end": 18}]},
                      "u2": {"file_id": "F2", "source_sha256": "def", "source_spans": [{"start": 2, "end": 8}]},
                      "u3": {"file_id": "F3", "source_sha256": "ghi", "source_spans": [{"start": 0, "end": 5}]}}

    def test_known_event_requires_exact_source_scope(self):
        self.assertEqual(e06.event_for_unit(self.units["u1"], self.graph)[0], "ev")

    def test_same_file_other_behavior_not_grouped(self):
        self.units["u1"]["source_spans"] = [{"start": 0, "end": 25}]
        self.assertIsNone(e06.event_for_unit(self.units["u1"], self.graph))

    def test_uncertain_event_not_grouped(self):
        self.graph["events"][0]["status"] = "uncertain"
        self.assertIsNone(e06.event_for_unit(self.units["u1"], self.graph))

    def test_diversify_keeps_model_rank_and_scores(self):
        hits = [{"unit_id": "u1", "file_id": "F1", "rank": 1, "score": 9.0},
                {"unit_id": "u2", "file_id": "F2", "rank": 2, "score": 8.0},
                {"unit_id": "u3", "file_id": "F3", "rank": 3, "score": 7.0}]
        result = e06.diversify(hits, self.units, self.graph)
        self.assertEqual([x["unit_id"] for x in result], ["u1", "u3", "u2"])
        self.assertEqual([x["rank"] for x in result], [1, 3, 2])
        self.assertEqual(result[-1]["score"], 8.0)

    def test_unknown_units_same_file_remain_independent(self):
        self.graph["events"] = []
        self.units["u2"]["file_id"] = "F1"
        hits = [{"unit_id":"u1","file_id":"F1","rank":1,"score":9},
                {"unit_id":"u2","file_id":"F1","rank":2,"score":8},
                {"unit_id":"u3","file_id":"F3","rank":3,"score":7}]
        self.assertEqual([h["unit_id"] for h in e06.diversify(hits,self.units,self.graph)], ["u1","u2","u3"])

    def test_reuse_rejects_changed_query_source_or_assessment(self):
        source='original evidence'
        hit={'file_id':'F1','unit_id':'u1','text':source,'rank':1,'score':1,
             'source_spans':[{'start':0,'end':len(source)}]}
        parent={'query_id':'Q1','text':'original query','files':[hit]}
        packet=e06.demo.make_packet({'query_id':'Q1','text':parent['text']},[hit],{'F1':source})
        judgment={'query_id':'Q1','input_sha256':packet['input_sha256'],
                  'packet_sha256':e06.demo.sha_json(packet),'human_approved':False,
                  'evidence_assessments':[{'file_id':'F1','unit_id':'u1','rank':1}]}
        e06.validate_parent_binding(parent,packet,judgment,{'F1':source})
        changed=copy.deepcopy(parent);changed['text']='different query'
        with self.assertRaises(ValueError):e06.validate_parent_binding(changed,packet,judgment,{'F1':source})
        with self.assertRaises(ValueError):e06.validate_parent_binding(parent,packet,judgment,{'F1':source+'changed'})
        changed=copy.deepcopy(judgment);changed['evidence_assessments'][0]['unit_id']='other'
        with self.assertRaises(ValueError):e06.validate_parent_binding(parent,packet,changed,{'F1':source})

if __name__ == "__main__": unittest.main()
