# Canonicalization Layer Architecture

## Mission
Transform raw source-grounded events into tool-agnostic canonical organizational memory while preserving provenance, temporal semantics, and replayability.

## Owns
- structural normalization of raw envelopes,
- deterministic extraction of explicit semantics,
- bounded AI-assisted extraction at ambiguity boundaries,
- ontology mapping into canonical models,
- ambiguity registration and confidence annotation,
- canonical persistence contracts.

## Does Not Own
- causal inference,
- strategic interpretation,
- executive synthesis,
- decision quality judgment,
- graph traversal intelligence.

## Input Contracts
- immutable raw events with source identity/version/provenance bootstrap fields,
- ontology definitions and mapping registry,
- extraction policy/version bundle.

## Output Contracts
- `CanonicalEvent`, `CanonicalEntity`, `CanonicalRelation`,
- canonical model projections (`Topic`, `Thread`, `Artifact`, `Decision`, `Action`),
- ambiguity records,
- provenance and confidence fields.

## Core Guarantees
- deterministic-first extraction pipeline,
- no mutation of raw truth,
- replay-comparable canonical outputs by version context,
- clear boundary between deterministic facts and inferred hypotheses.
