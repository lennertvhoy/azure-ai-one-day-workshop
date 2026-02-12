import json
import unittest

def extract_json_candidates(text):
    """
    Copy of the extraction logic from StudentManager.
    """
    candidates = []
    text = text.strip()
    idx = 0
    while idx < len(text):
        start_idx = text.find('{', idx)
        if start_idx == -1:
            break
        try:
            obj, end_idx = json.JSONDecoder().raw_decode(text[start_idx:])
            candidates.append(obj)
            idx = start_idx + end_idx
        except json.JSONDecodeError:
            idx = start_idx + 1
    return candidates

class TestJsonExtraction(unittest.TestCase):
    def test_clean_json(self):
        output = '{"invitedUser": {"id": "123"}}'
        candidates = extract_json_candidates(output)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['invitedUser']['id'], '123')

    def test_mixed_output_prefix(self):
        output = '[INFO] Inviting...\n{"invitedUser": {"id": "456"}}'
        candidates = extract_json_candidates(output)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['invitedUser']['id'], '456')

    def test_mixed_output_suffix(self):
        output = '{"invitedUser": {"id": "789"}}\n[INFO] Done.'
        candidates = extract_json_candidates(output)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['invitedUser']['id'], '789')

    def test_multiple_jsons(self):
        # The logic collects all candidates. The app logic then prioritizes the one with specific keys.
        output = '{"log": "info"}\n{"invitedUser": {"id": "abc"}}'
        candidates = extract_json_candidates(output)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[1]['invitedUser']['id'], 'abc')
    
    def test_nested_braces_in_log(self):
        output = '[INFO] {Starting} process\n{"invitedUser": {"id": "def"}}'
        candidates = extract_json_candidates(output)
        # The parser might try to parse '{Starting}' and fail, then continue.
        self.assertTrue(len(candidates) >= 1)
        found = any(c.get('invitedUser', {}).get('id') == 'def' for c in candidates)
        self.assertTrue(found)

if __name__ == '__main__':
    unittest.main()
