import unittest

from app.agent.events.pending_tasks import PendingApprovalTask, PendingTaskQueue


class PendingTaskTests(unittest.TestCase):
    def test_create_approve_reject_and_list(self):
        queue = PendingTaskQueue()
        first = queue.create(PendingApprovalTask(action="Send invitation", tool="gmail", reason="Meeting scheduled", priority="high"))
        second = queue.create(PendingApprovalTask(action="Create event", tool="calendar", reason="User requested"))

        approved = queue.approve(first.id, approved_by=5)
        rejected = queue.reject(second.id, approved_by=5)

        self.assertEqual(approved.status, "approved")
        self.assertEqual(approved.approved_by, 5)
        self.assertEqual(rejected.status, "rejected")
        self.assertEqual(queue.list("pending"), [])
