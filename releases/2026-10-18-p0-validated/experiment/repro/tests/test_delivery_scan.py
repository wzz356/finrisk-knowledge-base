import unittest
from seal_results import has_credential_like_value

class DeliveryScanTests(unittest.TestCase):
    def test_scope_word_ending_in_sk_is_not_a_credential(self):
        self.assertFalse(has_credential_like_value('finrisk-p0-effect-new36-20261018-v1'))
    def test_standalone_synthetic_key_like_values_are_detected(self):
        for prefix in ['"',' ',':','\n','']:
            self.assertTrue(has_credential_like_value(prefix+'sk-'+'z'*24))

if __name__=='__main__':unittest.main()
