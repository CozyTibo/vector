"""Generate ``octs-walk-api-v1.openapi.json`` from normative paths (**RULE API-0**).

Includes walk POST/GET/cancel (**P05-17**), **engine-identity** GET (**P05-21**),
**derived-index/replay-verify** (**P05-20**), **control-plane** GET (**P05-24**),
and **readiness-economics** GET (**P05-25**).
Run: ``python -m vector.scripts.generate_octs_walk_openapi``
(or ``make octs-openapi`` from repo root).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        if (root / "DOCS" / "cortex" / "05-traversal" / "schemas").is_dir():
            return root
    msg = "Could not locate DOCS/cortex/05-traversal/schemas"
    raise RuntimeError(msg)


def build_octs_walk_openapi_v1_document() -> dict[str, Any]:
    walk_req_ref = "../octs-walk-request-v1.schema.json"
    replay_verify_ref = "../octs-derived-index-replay-verify-v1.schema.json"
    err_details: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["error_code", "details"],
        "properties": {
            "error_code": {"type": "string"},
            "details": {
                "type": "object",
                "additionalProperties": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "integer"},
                        {"type": "boolean"},
                        {"type": "number"},
                    ]
                },
            },
        },
    }
    walk_id_param = {
        "name": "walk_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "format": "uuid"},
    }
    tid_param = {
        "name": "tid",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "format": "uuid"},
    }
    security = [{"admin_basic": []}]
    post_walks: dict[str, Any] = {
        "post": {
            "summary": "Submit OCTS walk (sync stub or async accept)",
            "security": security,
            "parameters": [
                tid_param,
                {
                    "name": "async",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "enum": ["0", "1"]},
                    "description": "When async=1, return 202 Accepted with job_id (stub).",
                },
            ],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": walk_req_ref},
                    }
                },
            },
            "responses": {
                "200": {"description": "Sync walk accepted and completed (stub)."},
                "202": {"description": "Async walk accepted (**RULE API-02**)."},
                "400": {
                    "description": "Validation / unsupported request",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
                "413": {
                    "description": "Sync caps exceeded (**FS-API-01**)",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
                "503": {
                    "description": "Engine identity unavailable for authoritative sync walk "
                    "(**ENG-03**, ``VECTOR_OCTS_ENFORCE_ENGINE_IDENTITY``).",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
            },
        }
    }
    post_replay_verify: dict[str, Any] = {
        "post": {
            "summary": "Derived index replay verify (recompute index_content_hash)",
            "security": security,
            "parameters": [tid_param],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": replay_verify_ref},
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Hash computed; double_run_equal when two passes agree (**G-P05-REPLAY-IDX-01**)."
                },
                "400": {
                    "description": "Schema or derived artifact invalid",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
                "409": {
                    "description": "expected_index_content_hash pin mismatch",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
            },
        }
    }
    get_walk: dict[str, Any] = {
        "get": {
            "summary": "Poll walk status / result (**RULE API-01**)",
            "security": security,
            "parameters": [tid_param, walk_id_param],
            "responses": {
                "200": {"description": "Poll: status enum; walk_result when completed."},
                "404": {
                    "description": "Unknown walk or tenant",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
            },
        }
    }
    cancel_walk: dict[str, Any] = {
        "post": {
            "summary": "Cooperative cancel",
            "security": security,
            "parameters": [tid_param, walk_id_param],
            "responses": {
                "200": {"description": "Cancelled or idempotent noop."},
                "400": {
                    "description": "Cannot cancel terminal walk",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
                "404": {
                    "description": "Unknown walk",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
            },
        }
    }
    get_engine_identity: dict[str, Any] = {
        "get": {
            "summary": "OCTS engine identity / build id pin (**P05-21**)",
            "security": security,
            "parameters": [tid_param],
            "responses": {
                "200": {
                    "description": "Resolved ``engine_build_id`` or unavailable diagnostic "
                    "(**ENG**; non-throwing)."
                },
                "404": {
                    "description": "Unknown tenant",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
            },
        }
    }
    get_control_plane: dict[str, Any] = {
        "get": {
            "summary": "OCTS traversal control plane aggregate (**P05-24**)",
            "security": security,
            "parameters": [
                tid_param,
                {
                    "name": "include_exploration",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "enum": ["0", "1", "true", "false"]},
                    "description": "Override **FS-CP-02** visibility for exploration partition rows.",
                },
            ],
            "responses": {
                "200": {"description": "Structural queue / abort classes / budget histogram."},
                "400": {
                    "description": "Invalid include_exploration query",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
                "404": {
                    "description": "Unknown tenant",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
            },
        }
    }
    get_readiness_economics: dict[str, Any] = {
        "get": {
            "summary": "OCTS readiness + economics numeric receipt (**P05-25**)",
            "security": security,
            "parameters": [
                tid_param,
                {
                    "name": "probe_profile",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "enum": ["clean", "hostile"]},
                    "description": "Pinned golden projection profile (**clean** default).",
                },
            ],
            "responses": {
                "200": {"description": "Sorted numeric stats + ``economics_receipt_hash``."},
                "400": {
                    "description": "Invalid probe_profile",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
                "404": {
                    "description": "Unknown tenant",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OctsApiErrorV1"}
                        }
                    },
                },
            },
        }
    }
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Cortex OCTS — admin traversal API (generated)",
            "version": "1.0.0",
            "description": (
                "Generated by vector.scripts.generate_octs_walk_openapi (**RULE API-0**): "
                "walks + engine identity + derived index replay verify + control plane + readiness economics."
            ),
        },
        "paths": {
            "/admin/tenants/{tid}/cortex/traversal/control-plane": get_control_plane,
            "/admin/tenants/{tid}/cortex/traversal/derived-index/replay-verify": post_replay_verify,
            "/admin/tenants/{tid}/cortex/traversal/engine-identity": get_engine_identity,
            "/admin/tenants/{tid}/cortex/traversal/readiness-economics": get_readiness_economics,
            "/admin/tenants/{tid}/cortex/traversal/walks": post_walks,
            "/admin/tenants/{tid}/cortex/traversal/walks/{walk_id}": get_walk,
            "/admin/tenants/{tid}/cortex/traversal/walks/{walk_id}/cancel": cancel_walk,
        },
        "components": {
            "securitySchemes": {
                "admin_basic": {
                    "type": "http",
                    "scheme": "basic",
                    "description": "Admin HTTP basic (same as other /admin routes).",
                }
            },
            "schemas": {"OctsApiErrorV1": err_details},
        },
    }


def main() -> None:
    root = _repo_root()
    out = (
        root
        / "DOCS"
        / "cortex"
        / "05-traversal"
        / "schemas"
        / "generated"
        / "octs-walk-api-v1.openapi.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = build_octs_walk_openapi_v1_document()
    out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
