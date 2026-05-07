# Cognition Trust Model

## Trust Objective
Help operators determine if Cortex outputs are trustworthy enough for operational use.

## Trust Inputs
- provenance completeness,
- replay consistency,
- ambiguity pressure,
- confidence distributions,
- corruption signals,
- phase health and drift indicators.

## Trust States
- `TRUSTED`
- `CONDITIONALLY_TRUSTED`
- `UNTRUSTED`

## Trust Rules
- no provenance -> never trusted.
- unresolved critical replay divergence -> untrusted.
- high ambiguity with low confidence -> conditional.

## Operator Guidance
Trust view must explain:
- why trust changed,
- what evidence drives current state,
- what action can restore trust.
