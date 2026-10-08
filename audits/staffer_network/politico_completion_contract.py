"""Explicit acquisition completion with evidence-backed source exceptions.

Completion is an acquisition outcome, never a claim of complete field content.
"""
import re

SOURCE_EXCEPTION_POLICY = 'browser-checked-source-omissions-20260905-v1'
SHA256 = re.compile(r'^[0-9a-f]{64}$')


def completion_accepted(receipt, *, legacy_default=False):
    status = receipt.get('completion_status', 'COMPLETE' if legacy_default else None)
    if status == 'COMPLETE':
        return True
    if status != 'COMPLETE_WITH_EXCEPTIONS':
        return False
    proof = receipt.get('source_exception_verification') or {}
    count = proof.get('accepted_count')
    return bool(
        proof.get('status') == 'PASS'
        and proof.get('policy') == SOURCE_EXCEPTION_POLICY
        and isinstance(count, int) and not isinstance(count, bool) and count > 0
        and count == proof.get('source_incomplete_count')
        and SHA256.fullmatch(str(proof.get('evidence_sha256', '')))
        and SHA256.fullmatch(str(proof.get('profile_prefix_sha256', '')))
        and proof.get('profile_prefix_sha256') == receipt.get(
            'profile_prefix_sha256', proof.get('profile_prefix_sha256'))
    )


def validate_browser_exception(row, observation):
    """Require an exact source binding and an observed terminal browser outcome.

The caller separately validates the saved HTTP-200 API evidence. Rendered 404s
are labeled unavailable pages; retained API history is not discarded or turned
into a claimed API 404. Loading, login, timeouts, and generic errors never pass.
"""
    if not isinstance(observation, dict):
        return False
    expected_url = 'https://directory.politicopro.com/congress/staffer/' + row['profile_uuid']
    missing = [field for field in ('current_header_positions', 'employment_history') if not row.get(field)]
    if not (
        observation.get('profile_uuid') == row['profile_uuid']
        and observation.get('observed_url') == expected_url
        and observation.get('projected_api_sha256') == row.get('projected_api_sha256')
        and observation.get('source_missing_collections') == missing
        and observation.get('loading') is False
        and observation.get('observed_at')
        and observation.get('method') == 'BROWSER_RENDERED_PROFILE'
    ):
        return False
    headings = observation.get('headings') or []
    if observation.get('outcome') == 'RENDERED_SOURCE_UNAVAILABLE':
        return headings == ['404 Error', 'We’re sorry, but the page cannot be found']
    if observation.get('outcome') != 'RENDERED_SOURCE_MISSING_COLLECTIONS':
        return False
    return bool(
        row.get('verified_name') in headings
        and '404 Error' not in headings
        and ('employment_history' not in missing or 'Employment History' not in headings)
        and ('current_header_positions' not in missing or observation.get('current_header_positions') == [])
    )
