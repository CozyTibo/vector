"""Stable registry ids seeded in migration `20260324_0011_step3_canonical_ontology`."""

from __future__ import annotations

# artifact_kind.id
ARTIFACT_KIND_REPOSITORY = 1
ARTIFACT_KIND_TRACKABLE_UNIT = 2
ARTIFACT_KIND_CHANGESET = 3
ARTIFACT_KIND_REVISION = 4

# relation_kind.id
RELATION_AUTHORED_BY = 1
RELATION_ASSOCIATED_WITH = 2
RELATION_CONTAINS = 3
RELATION_ASSIGNED_TO = 4
RELATION_COMMENTED_ON = 5

RULE_VERSION = "github_canonical@v1"
RULE_SOURCE_GITHUB = "vector.domains.canonical.github_mapper"

RULE_VERSION_LINEAR = "linear_canonical@v1"
RULE_SOURCE_LINEAR = "vector.domains.canonical.linear_mapper"

RELATIONSHIP_SOURCE_CONNECTOR = "asserted_connector"
