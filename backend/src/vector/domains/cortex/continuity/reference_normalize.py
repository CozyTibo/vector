"""Deterministic cross-tool reference normalization (no identity merge, no inference)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from vector.domains.cortex.continuity.reference_schema import (
    REFERENCE_CONTRACT_VERSION,
    NormalizedReference,
    ReferenceFamily,
)

_HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")
_HEX7_40 = re.compile(r"^[0-9a-fA-F]{7,40}$")
_FULL_NAME = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _strip(s: str | None) -> str:
    return s.strip() if isinstance(s, str) else ""


def normalize_git_repository_full_name(
    value: str | None,
    *,
    source_paths: list[str] | None = None,
) -> NormalizedReference:
    """Normalize ``owner/repo`` (case-sensitive segments preserved; internal whitespace stripped)."""
    s = _strip(value)
    if not s:
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.GIT_REPOSITORY,
            "status": "unknown",
            "canonical_form": "",
            "components": {},
            "source_paths": list(source_paths or []),
        }
    # Accept URL path last two segments for github.com
    if "github.com" in s or s.startswith("http://") or s.startswith("https://"):
        parsed = urlparse(s if "://" in s else f"https://{s}")
        path = parsed.path.strip("/")
        parts = path.split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            fn = f"{owner}/{repo}"
            if _FULL_NAME.match(fn):
                return {
                    "reference_contract_version": REFERENCE_CONTRACT_VERSION,
                    "family": ReferenceFamily.GIT_REPOSITORY,
                    "status": "ok",
                    "canonical_form": f"git.repo:{fn}",
                    "components": {"full_name": fn, "owner": owner, "name": repo},
                    "source_paths": list(source_paths or []),
                }
    if "/" in s and _FULL_NAME.match(s):
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.GIT_REPOSITORY,
            "status": "ok",
            "canonical_form": f"git.repo:{s}",
            "components": {"full_name": s, "owner": s.split("/", 1)[0], "name": s.split("/", 1)[1]},
            "source_paths": list(source_paths or []),
        }
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.GIT_REPOSITORY,
        "status": "invalid",
        "canonical_form": "",
        "components": {"raw": s},
        "source_paths": list(source_paths or []),
    }


def normalize_git_commit_sha(
    value: str | None,
    *,
    source_paths: list[str] | None = None,
) -> NormalizedReference:
    """Normalize commit SHA; 40-char hex is ``ok``; shorter hex is ``partial`` (collision risk explicit)."""
    s = _strip(value)
    if not s:
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.GIT_COMMIT,
            "status": "unknown",
            "canonical_form": "",
            "components": {},
            "source_paths": list(source_paths or []),
        }
    if _HEX40.match(s):
        low = s.lower()
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.GIT_COMMIT,
            "status": "ok",
            "canonical_form": f"git.commit:{low}",
            "components": {"sha": low, "length": 40},
            "source_paths": list(source_paths or []),
        }
    if _HEX7_40.match(s) and len(s) < 40:
        low = s.lower()
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.GIT_COMMIT,
            "status": "partial",
            "canonical_form": f"git.commit.prefix:{low}",
            "components": {"sha_prefix": low, "length": len(low)},
            "source_paths": list(source_paths or []),
        }
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.GIT_COMMIT,
        "status": "invalid",
        "canonical_form": "",
        "components": {"raw": s},
        "source_paths": list(source_paths or []),
    }


def normalize_github_pull_request_ref(
    repository_full_name: str | None,
    number: Any,
    *,
    source_paths: list[str] | None = None,
) -> NormalizedReference:
    repo = normalize_git_repository_full_name(repository_full_name, source_paths=source_paths)
    if repo["status"] != "ok":
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.GITHUB_PULL_REQUEST,
            "status": "unknown" if repo["status"] == "unknown" else "invalid",
            "canonical_form": "",
            "components": {"repository": repo},
            "source_paths": list(source_paths or []),
        }
    if isinstance(number, str) and number.strip().isdigit():
        n = int(number.strip())
    elif isinstance(number, int):
        n = number
    else:
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.GITHUB_PULL_REQUEST,
            "status": "invalid",
            "canonical_form": "",
            "components": {"repository": repo, "number": number},
            "source_paths": list(source_paths or []),
        }
    fn = str(repo["components"].get("full_name", ""))
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.GITHUB_PULL_REQUEST,
        "status": "ok",
        "canonical_form": f"github.pr:{fn}#{n}",
        "components": {"repository_full_name": fn, "number": n},
        "source_paths": list(source_paths or []),
    }


def normalize_github_issue_ref(
    repository_full_name: str | None,
    number: Any,
    *,
    source_paths: list[str] | None = None,
) -> NormalizedReference:
    repo = normalize_git_repository_full_name(repository_full_name, source_paths=source_paths)
    if repo["status"] != "ok":
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.GITHUB_ISSUE,
            "status": "unknown" if repo["status"] == "unknown" else "invalid",
            "canonical_form": "",
            "components": {"repository": repo},
            "source_paths": list(source_paths or []),
        }
    if isinstance(number, str) and number.strip().isdigit():
        n = int(number.strip())
    elif isinstance(number, int):
        n = number
    else:
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.GITHUB_ISSUE,
            "status": "invalid",
            "canonical_form": "",
            "components": {"repository": repo, "number": number},
            "source_paths": list(source_paths or []),
        }
    fn = str(repo["components"].get("full_name", ""))
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.GITHUB_ISSUE,
        "status": "ok",
        "canonical_form": f"github.issue:{fn}#{n}",
        "components": {"repository_full_name": fn, "number": n},
        "source_paths": list(source_paths or []),
    }


def normalize_github_workflow_run_id(
    repository_full_name: str | None,
    run_id: Any,
    *,
    source_paths: list[str] | None = None,
) -> NormalizedReference:
    repo = normalize_git_repository_full_name(repository_full_name, source_paths=source_paths)
    rid_s = str(run_id).strip() if run_id is not None else ""
    if not rid_s or repo["status"] != "ok":
        st = "unknown" if not rid_s and repo["status"] == "unknown" else "invalid"
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.GITHUB_WORKFLOW_RUN,
            "status": st,
            "canonical_form": "",
            "components": {"repository": repo, "run_id": run_id},
            "source_paths": list(source_paths or []),
        }
    fn = str(repo["components"].get("full_name", ""))
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.GITHUB_WORKFLOW_RUN,
        "status": "ok",
        "canonical_form": f"github.workflow_run:{fn}:{rid_s}",
        "components": {"repository_full_name": fn, "run_id": rid_s},
        "source_paths": list(source_paths or []),
    }


def normalize_github_deployment_id(
    repository_full_name: str | None,
    deployment_id: Any,
    *,
    source_paths: list[str] | None = None,
) -> NormalizedReference:
    repo = normalize_git_repository_full_name(repository_full_name, source_paths=source_paths)
    did_s = str(deployment_id).strip() if deployment_id is not None else ""
    if not did_s or repo["status"] != "ok":
        st = "unknown" if not did_s and repo["status"] == "unknown" else "invalid"
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.GITHUB_DEPLOYMENT,
            "status": st,
            "canonical_form": "",
            "components": {"repository": repo, "deployment_id": deployment_id},
            "source_paths": list(source_paths or []),
        }
    fn = str(repo["components"].get("full_name", ""))
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.GITHUB_DEPLOYMENT,
        "status": "ok",
        "canonical_form": f"github.deployment:{fn}:{did_s}",
        "components": {"repository_full_name": fn, "deployment_id": did_s},
        "source_paths": list(source_paths or []),
    }


def normalize_slack_message_ref(
    channel_id: str | None,
    message_ts: str | None,
    *,
    source_paths: list[str] | None = None,
) -> NormalizedReference:
    ch = _strip(channel_id)
    ts = _strip(message_ts)
    if not ch or not ts:
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.SLACK_MESSAGE,
            "status": "unknown",
            "canonical_form": "",
            "components": {"channel_id": ch or None, "ts": ts or None},
            "source_paths": list(source_paths or []),
        }
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.SLACK_MESSAGE,
        "status": "ok",
        "canonical_form": f"slack.msg:{ch}:{ts}",
        "components": {"channel_id": ch, "ts": ts},
        "source_paths": list(source_paths or []),
    }


def normalize_slack_thread_ref(
    channel_id: str | None,
    thread_ts: str | None,
    *,
    source_paths: list[str] | None = None,
) -> NormalizedReference:
    ch = _strip(channel_id)
    tts = _strip(thread_ts)
    if not ch or not tts:
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.SLACK_THREAD,
            "status": "unknown",
            "canonical_form": "",
            "components": {"channel_id": ch or None, "thread_ts": tts or None},
            "source_paths": list(source_paths or []),
        }
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.SLACK_THREAD,
        "status": "ok",
        "canonical_form": f"slack.thread:{ch}:{tts}",
        "components": {"channel_id": ch, "thread_ts": tts},
        "source_paths": list(source_paths or []),
    }


def normalize_linear_issue_ref(issue_id: str | None, *, source_paths: list[str] | None = None) -> NormalizedReference:
    s = _strip(issue_id)
    if not s:
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.LINEAR_ISSUE,
            "status": "unknown",
            "canonical_form": "",
            "components": {},
            "source_paths": list(source_paths or []),
        }
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.LINEAR_ISSUE,
        "status": "ok",
        "canonical_form": f"linear.issue:{s}",
        "components": {"issue_id": s},
        "source_paths": list(source_paths or []),
    }


def normalize_notion_page_ref(page_id: str | None, *, source_paths: list[str] | None = None) -> NormalizedReference:
    s = _strip(page_id)
    if not s:
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.NOTION_PAGE,
            "status": "unknown",
            "canonical_form": "",
            "components": {},
            "source_paths": list(source_paths or []),
        }
    # Notion IDs often UUID-like with dashes; preserve as given (normalized strip only).
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.NOTION_PAGE,
        "status": "ok",
        "canonical_form": f"notion.page:{s}",
        "components": {"page_id": s},
        "source_paths": list(source_paths or []),
    }


def normalize_http_url(url: str | None, *, source_paths: list[str] | None = None) -> NormalizedReference:
    s = _strip(url)
    if not s:
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.URL_HTTP,
            "status": "unknown",
            "canonical_form": "",
            "components": {},
            "source_paths": list(source_paths or []),
        }
    parsed = urlparse(s if "://" in s else f"https://{s}")
    if not parsed.netloc:
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.URL_HTTP,
            "status": "invalid",
            "canonical_form": "",
            "components": {"raw": s},
            "source_paths": list(source_paths or []),
        }
    # Deterministic: scheme lower, netloc lower, path without trailing slash for key (except root)
    scheme = (parsed.scheme or "https").lower()
    host = parsed.netloc.lower()
    path = parsed.path or ""
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    canonical = f"{scheme}://{host}{path}"
    q = f"?{parsed.query}" if parsed.query else ""
    frag = f"#{parsed.fragment}" if parsed.fragment else ""
    full = f"{canonical}{q}{frag}"
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.URL_HTTP,
        "status": "ok",
        "canonical_form": f"url:{full}",
        "components": {"url": full, "origin": f"{scheme}://{host}"},
        "source_paths": list(source_paths or []),
    }


def normalize_email_address(email: str | None, *, source_paths: list[str] | None = None) -> NormalizedReference:
    s = _strip(email).lower()
    if not s:
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.EMAIL_ADDRESS,
            "status": "unknown",
            "canonical_form": "",
            "components": {},
            "source_paths": list(source_paths or []),
        }
    if not _EMAIL_RE.match(s):
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.EMAIL_ADDRESS,
            "status": "invalid",
            "canonical_form": "",
            "components": {"raw": email},
            "source_paths": list(source_paths or []),
        }
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.EMAIL_ADDRESS,
        "status": "ok",
        "canonical_form": f"email:{s}",
        "components": {"email": s},
        "source_paths": list(source_paths or []),
    }


def normalize_opaque_external(provider: str, key: str | None, *, source_paths: list[str] | None = None) -> NormalizedReference:
    """Last-resort stable key: provider + exact external string (no parsing)."""
    p = _strip(provider)
    k = _strip(key)
    if not p or not k:
        return {
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
            "family": ReferenceFamily.OPAQUE_EXTERNAL,
            "status": "unknown",
            "canonical_form": "",
            "components": {"provider": p or None, "key": k or None},
            "source_paths": list(source_paths or []),
        }
    return {
        "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        "family": ReferenceFamily.OPAQUE_EXTERNAL,
        "status": "ok",
        "canonical_form": f"opaque:{p}:{k}",
        "components": {"provider": p, "key": k},
        "source_paths": list(source_paths or []),
    }
