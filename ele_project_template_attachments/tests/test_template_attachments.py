from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTemplateAttachments(TransactionCase):

    def _attachments(self, project):
        return self.env["ir.attachment"].search([
            ("res_model", "=", "project.project"),
            ("res_id", "=", project.id),
            ("res_field", "=", False),
        ])

    def test_attachments_copied_independently(self):
        template = self.env["project.project"].create({
            "name": "Template", "is_template": True,
        })
        self.env["ir.attachment"].create({
            "name": "guide.txt",
            "raw": b"hello",
            "res_model": "project.project",
            "res_id": template.id,
        })
        p1 = template.copy({"name": "Client A", "is_template": False})
        p2 = template.copy({"name": "Client B", "is_template": False})

        a1, a2 = self._attachments(p1), self._attachments(p2)
        self.assertEqual(a1.mapped("name"), ["guide.txt"])
        self.assertEqual(a2.mapped("name"), ["guide.txt"])
        self.assertEqual(a1.raw, b"hello")
        self.assertNotEqual(a1.id, a2.id)

        a1.unlink()
        self.assertTrue(self._attachments(p2))
        self.assertTrue(self._attachments(template))

    def test_normal_project_copy_has_no_extra(self):
        normal = self.env["project.project"].create({"name": "Normal"})
        self.env["ir.attachment"].create({
            "name": "x.txt", "raw": b"x",
            "res_model": "project.project", "res_id": normal.id,
        })
        copy = normal.copy()
        self.assertFalse(self._attachments(copy))

    def test_save_as_template_keeps_attachments(self):
        project = self.env["project.project"].create({"name": "Source"})
        self.env["ir.attachment"].create({
            "name": "keep.txt", "raw": b"k",
            "res_model": "project.project", "res_id": project.id,
        })
        template = project.copy({"name": "Tpl", "is_template": True})
        self.assertEqual(self._attachments(template).mapped("name"), ["keep.txt"])
        self.assertTrue(self._attachments(project))

    def test_task_attachments_copied(self):
        template = self.env["project.project"].create({
            "name": "Tpl2", "is_template": True,
        })
        task = self.env["project.task"].create({
            "name": "T1", "project_id": template.id,
        })
        self.env["ir.attachment"].create({
            "name": "task_file.txt", "raw": b"t",
            "res_model": "project.task", "res_id": task.id,
        })
        project = template.action_create_from_template({"name": "Client X"})
        new_task = self.env["project.task"].search([("project_id", "=", project.id)])
        files = self.env["ir.attachment"].search([
            ("res_model", "=", "project.task"),
            ("res_id", "in", new_task.ids),
            ("res_field", "=", False),
        ])
        self.assertEqual(files.mapped("name"), ["task_file.txt"])
        self.assertEqual(files.raw, b"t")

    def test_convert_to_template_keeps_task_attachments(self):
        project = self.env["project.project"].create({"name": "Src2"})
        task = self.env["project.task"].create({
            "name": "T2", "project_id": project.id,
        })
        self.env["ir.attachment"].create({
            "name": "t2.txt", "raw": b"2",
            "res_model": "project.task", "res_id": task.id,
        })
        template = project.with_context(convert_to_template=True).copy(
            {"is_template": True})
        new_task = self.env["project.task"].search([("project_id", "=", template.id)])
        files = self.env["ir.attachment"].search([
            ("res_model", "=", "project.task"), ("res_id", "in", new_task.ids),
        ])
        self.assertEqual(files.mapped("name"), ["t2.txt"])
