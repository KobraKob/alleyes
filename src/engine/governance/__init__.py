"""Governance, policies, approvals, and kill switch module."""

from src.engine.governance.actions import ActionRecord, propose_action
from src.engine.governance.approvals import list_pending_approvals, submit_approval
from src.engine.governance.audit import write_audit_log
from src.engine.governance.executor import execute_action
from src.engine.governance.kill_switch import is_kill_switch_engaged, set_kill_switch

__all__ = [
    "propose_action",
    "ActionRecord",
    "execute_action",
    "list_pending_approvals",
    "submit_approval",
    "set_kill_switch",
    "is_kill_switch_engaged",
    "write_audit_log",
]
