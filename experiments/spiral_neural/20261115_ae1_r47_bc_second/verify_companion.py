"""Read-only R47 companion verifier. Run with path to *extracted* experiment root.

This public Git entry contains no model weights and does not train anything.
The complete 249-entry companion ZIP is supplied separately.
"""
import hashlib
import pathlib
import sys

EXPECTED = {
    "r47_bc_second_route.py": "82733e323816443402f65b0bfb2cc5b84bb83a2955129bc252c56b6ddc90bc6f",
    "r47_manifest.jsonl": "d8900796e8e50c116d9b780f42377e5ef40332623a3dd39a448903dec57e8416",
    "r47_prereg.json": "1f2fd472d3130bc23dd0f3d7409efddcf5c9306825d51980a4fe53ca1062c753",
    "r47_outputs/raw_results.jsonl": "03719252666d9ce03ead32d9e82341889e00a95185a00cc9c9ea9841e7fe09cf",
    "r47_outputs/results.json": "b1f0ea321fcbb3bd9077288981a1be872d0b71f7deed0e8e1c38ff44f0205e8a",
    "r47_outputs/weights_101_dual.json": "a79907486dd8b2d400afaf1ef6a2c1458c81b73d612f3051b665d856ed1450aa",
    "r47_outputs/weights_202_dual.json": "d4fe9ebac8503fe330ade05bc5e7bc6d716347fef23e9d8247abcd447bdad4cf",
    "r47_outputs/weights_303_dual.json": "e9af4d4cfe15f6a7234c0e1e5a61cad6b0a3aaaf6203519390d7f217d45c6257",
}
def main() -> None:
    root = pathlib.Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
    for relative, digest in EXPECTED.items():
        p=(root/relative).resolve()
        assert p.is_relative_to(root) and p.is_file(), relative
        assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, relative
    manifest=(root/"R47_SHA256SUMS")
    assert manifest.is_file(), "full SHA256 manifest missing"
    seen=set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        actual_digest, relative=line.split("  ",1)
        assert relative not in seen, relative
        seen.add(relative)
        p=(root/relative).resolve()
        assert p.is_relative_to(root) and p.is_file(), relative
        assert hashlib.sha256(p.read_bytes()).hexdigest() == actual_digest, relative
    assert len(seen)==248, len(seen)
    print("R47 hash verification PASS:",len(seen),"files, 8 fixed checkpoints/source fingerprints")
    print("Actual NN replay still requires: python r47_bc_second_route.py replay; python r47_bc_second_route.py numpy")
if __name__=="__main__":
    main()
