import unittest
try:
    from rebind_dates import matching_date_quote
except ImportError:
    matching_date_quote=None

class DateEvidence(unittest.TestCase):
    def test_same_complete_date_rebound_to_exact_source_without_changing_value(self):
        self.assertIsNotNone(matching_date_quote)
        self.assertEqual(matching_date_quote('2015-11-27','处罚决定。\n2015年11月27日\n手机扫一扫打开此页'),'2015年11月27日')

    def test_incomplete_ambiguous_or_different_date_has_no_automatic_rebinding(self):
        self.assertIsNotNone(matching_date_quote)
        for value,text in [('2025年','2025年1月2日'),('手机扫一扫打开此页','2025年1月2日'),
                           ('2015-11-27','2015年11月28日'),('2015-11-27','2015年11月27日与2015-11-27')]:
            self.assertIsNone(matching_date_quote(value,text))

if __name__=='__main__':unittest.main()
