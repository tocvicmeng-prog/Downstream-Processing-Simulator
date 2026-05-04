"""B-2d (W-011) tests: deterministic process dossier export."""

from __future__ import annotations

import json

from dpsim.core.process_dossier import (
    ProcessDossier,
    build_dossier,
    compute_calibration_store_hash,
    compute_dossier_hash,
    compute_recipe_hash,
    get_git_commit_short,
    get_package_versions,
)


SAMPLE_RECIPE_TOML = """\
[target]
name = "Protein A microsphere"

[material]
polymer_family = "agarose_chitosan"
"""


# ─── Hash determinism ────────────────────────────────────────────────────────


class TestHashDeterminism:
    def test_recipe_hash_stable(self):
        h1 = compute_recipe_hash(SAMPLE_RECIPE_TOML)
        h2 = compute_recipe_hash(SAMPLE_RECIPE_TOML)
        assert h1 == h2
        assert len(h1) == 64

    def test_recipe_hash_changes_with_byte(self):
        h1 = compute_recipe_hash(SAMPLE_RECIPE_TOML)
        h2 = compute_recipe_hash(SAMPLE_RECIPE_TOML + "\n")
        assert h1 != h2

    def test_calibration_hash_invariant_under_reorder(self):
        e1 = [
            {"profile_key": "cnbr_activation", "parameter_name": "k_forward", "measured_value": 1e-3},
            {"profile_key": "cdi_activation",  "parameter_name": "k_forward", "measured_value": 5e-4},
        ]
        e2 = list(reversed(e1))
        assert compute_calibration_store_hash(e1) == compute_calibration_store_hash(e2)

    def test_calibration_hash_invariant_under_dict_order(self):
        e1 = [{"profile_key": "x", "parameter_name": "y", "measured_value": 1.0}]
        e2 = [{"measured_value": 1.0, "parameter_name": "y", "profile_key": "x"}]
        assert compute_calibration_store_hash(e1) == compute_calibration_store_hash(e2)

    def test_empty_calibration_hashes_to_empty_blob_sha(self):
        import hashlib
        assert compute_calibration_store_hash([]) == hashlib.sha256(b"").hexdigest()


# ─── Builder shape ───────────────────────────────────────────────────────────


class TestBuilder:
    def test_minimal_inputs_build(self):
        dossier = build_dossier(recipe_toml=SAMPLE_RECIPE_TOML)
        assert dossier.recipe_toml == SAMPLE_RECIPE_TOML
        assert dossier.recipe_hash == compute_recipe_hash(SAMPLE_RECIPE_TOML)
        assert dossier.calibration_store_hash == compute_calibration_store_hash([])
        assert dossier.dpsim_version  # populated from dpsim.__version__
        assert dossier.timestamp_utc.endswith("+00:00")
        assert dossier.smoke_status == "not_run"

    def test_all_inputs_populate_fields(self):
        dossier = build_dossier(
            recipe_toml=SAMPLE_RECIPE_TOML,
            resolved_parameters={"rpm": 10000},
            m1_contract={"d32_um": 100.0},
            m2_contract={"step_count": 5},
            m3_contract={"DBC_mg_per_mL": 42.0},
            result_graph=[{"node": "M1"}],
            manifests=[{"model_name": "L1.PBE"}],
            calibration_entries=[
                {"profile_key": "p", "parameter_name": "q", "measured_value": 1.0}
            ],
            validation_blockers=[{"code": "FP_X", "severity": "blocker"}],
            validation_warnings=[{"code": "FP_Y", "severity": "warning"}],
            smoke_status="pass",
            notes="hello",
        )
        assert dossier.m1_contract == {"d32_um": 100.0}
        assert dossier.m2_contract == {"step_count": 5}
        assert dossier.m3_contract == {"DBC_mg_per_mL": 42.0}
        assert dossier.smoke_status == "pass"
        assert dossier.notes == "hello"
        assert len(dossier.calibration_entries) == 1
        assert len(dossier.validation_blockers) == 1
        assert len(dossier.validation_warnings) == 1

    def test_package_versions_includes_python(self):
        versions = get_package_versions()
        assert "python" in versions
        assert "platform" in versions


# ─── Serialisation round-trip ────────────────────────────────────────────────


class TestSerialisation:
    def test_to_dict_round_trip(self):
        dossier = build_dossier(
            recipe_toml=SAMPLE_RECIPE_TOML,
            resolved_parameters={"k": 1},
            calibration_entries=[
                {"profile_key": "p", "parameter_name": "q", "measured_value": 1.0}
            ],
        )
        recovered = ProcessDossier.from_dict(dossier.to_dict())
        assert recovered.recipe_toml == dossier.recipe_toml
        assert recovered.recipe_hash == dossier.recipe_hash
        assert recovered.calibration_store_hash == dossier.calibration_store_hash
        assert recovered.calibration_entries == dossier.calibration_entries
        assert recovered.dpsim_version == dossier.dpsim_version

    def test_json_round_trip(self):
        dossier = build_dossier(
            recipe_toml=SAMPLE_RECIPE_TOML,
            calibration_entries=[
                {"profile_key": "p", "parameter_name": "q", "measured_value": 1.0}
            ],
        )
        blob = dossier.to_json()
        # JSON must parse cleanly.
        parsed = json.loads(blob)
        assert parsed["recipe_hash"] == dossier.recipe_hash

    def test_write_and_read_json_round_trip(self, tmp_path):
        dossier = build_dossier(recipe_toml=SAMPLE_RECIPE_TOML)
        path = tmp_path / "dossier.json"
        dossier.write_json(path)
        recovered = ProcessDossier.read_json(path)
        assert recovered.recipe_hash == dossier.recipe_hash
        assert recovered.recipe_toml == dossier.recipe_toml

    def test_deterministic_json_excluding_timestamp(self):
        """Two builds of the same recipe at different times must produce
        identical content-hash JSON when timestamp + pkg versions excluded."""
        d1 = build_dossier(recipe_toml=SAMPLE_RECIPE_TOML, smoke_status="pass")
        d2 = build_dossier(recipe_toml=SAMPLE_RECIPE_TOML, smoke_status="pass")
        # Force differing timestamps (build_dossier captures time-of-call).
        d2.timestamp_utc = "1970-01-01T00:00:00+00:00"
        d2.package_versions = {"forced": "different"}
        # Force same git state (in case tests run in different repo contexts)
        d2.git_commit = d1.git_commit
        d2.git_dirty = d1.git_dirty
        h1 = compute_dossier_hash(d1)
        h2 = compute_dossier_hash(d2)
        assert h1 == h2


# ─── Tamper detection ───────────────────────────────────────────────────────


class TestTamperDetection:
    def test_recipe_hash_detects_recipe_mutation(self):
        dossier = build_dossier(recipe_toml=SAMPLE_RECIPE_TOML)
        original_hash = dossier.recipe_hash
        dossier.recipe_toml = SAMPLE_RECIPE_TOML + "\n# tampered"
        # Recompute on the mutated content; the stored hash should mismatch.
        recomputed = compute_recipe_hash(dossier.recipe_toml)
        assert recomputed != original_hash

    def test_calibration_hash_detects_value_change(self):
        e_before = [{"profile_key": "p", "parameter_name": "q", "measured_value": 1.0}]
        e_after = [{"profile_key": "p", "parameter_name": "q", "measured_value": 2.0}]
        assert compute_calibration_store_hash(e_before) != compute_calibration_store_hash(e_after)


# ─── Environment helpers (smoke) ────────────────────────────────────────────


class TestEnvironmentHelpers:
    def test_get_git_commit_returns_string(self):
        # In CI / dev checkouts, git is usually present and we get a SHA;
        # in environments without git, we get "". Either is acceptable.
        sha = get_git_commit_short()
        assert isinstance(sha, str)

    def test_get_package_versions_resolves_numpy(self):
        versions = get_package_versions(packages=["numpy"])
        assert "numpy" in versions
        # Either a real version string or "unavailable" — both are str.
        assert isinstance(versions["numpy"], str)
