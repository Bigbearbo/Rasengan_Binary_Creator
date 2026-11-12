import unittest
from audit import gate_shape, scope_of, digest, FROZEN_MANIFEST_SHA256

# Synthetic reproduction of observed call-site guards; NOT the original NN runner.
SOURCE = '''
def validate_inputs(path, approved):
    assert approved and file_sha(path) == approved, "Explicit approved manifest SHA missing or differs"
    return {}, None, [], {}, {}

def execute(manifest_path, approved, commit, output):
    assert re.fullmatch(r"[0-9a-f]{40}", commit or ""), "Coordinator preregistration commit required"
    manifest, cls, pool, initials, courses = validate_inputs(manifest_path, approved)
    for seed in []:
        run_seed(cls, initials[str(seed)], courses[str(seed)], pool, output, seed)
'''


class AuditTest(unittest.TestCase):
    def test_sha256_known_vector(self):
        self.assertEqual(digest(b"abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_functions_identified(self):
        self.assertIn("approved", scope_of(SOURCE, "validate_inputs"))
        self.assertIn("run_seed", scope_of(SOURCE, "execute"))

    def test_shape_is_not_authorization(self):
        result = gate_shape(SOURCE)
        self.assertTrue(result["commit_only_shape_checked"])
        self.assertTrue(result["manifest_hash_compared_to_caller_input"])
        self.assertTrue(result["formal_training_called_from_execute"])
        self.assertFalse(result["commit_bound_to_manifest_by_execute"])
        self.assertTrue(result["any_40hex_meets_shape"])

    def test_published_manifest_digest_shape(self):
        self.assertEqual(len(FROZEN_MANIFEST_SHA256), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in FROZEN_MANIFEST_SHA256))


if __name__ == "__main__":
    unittest.main()
