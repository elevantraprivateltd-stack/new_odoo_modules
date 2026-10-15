import logging

from odoo import models

from .project_task import _copy_attachments

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    _inherit = "project.project"

    def copy(self, default=None):
        """Copy project-level attachments whenever a template is involved:
        - project -> template   (Convert into template)
        - template -> project   (Create project from template)
        - template -> template  (Duplicate)
        (Task attachments are handled in project.task.copy.)
        """
        new_projects = super().copy(default=default)

        # is_template is native in Odoo 19 project; guard anyway.
        if "is_template" not in self._fields:
            return new_projects

        for source, new_project in zip(self, new_projects):
            if source.is_template or new_project.is_template:
                source._copy_template_attachments_to(new_project)
        return new_projects

    def _copy_template_attachments_to(self, new_project):
        self.ensure_one()
        project_files = _copy_attachments(self.env, self, new_project)

        # Task files were copied by project.task.copy(); count them for feedback.
        new_tasks = self.env["project.task"].with_context(active_test=False).sudo().search(
            [("project_id", "=", new_project.id)]
        )
        task_files = self.env["ir.attachment"].sudo().search_count([
            ("res_model", "=", "project.task"),
            ("res_id", "in", new_tasks.ids),
            ("res_field", "=", False),
        ])

        _logger.info(
            "ele_project_template_attachments: %s project file(s) and %s task file(s) copied "
            "from project %s (id %s) to %s (id %s)",
            project_files, task_files, self.name, self.id, new_project.name, new_project.id,
        )

        if project_files or task_files:
            body = self.env._(
                "Files copied from \"%(name)s\": %(pf)s project file(s), %(tf)s task file(s).",
                name=self.name, pf=project_files, tf=task_files,
            )
        else:
            body = self.env._(
                "No files were found on \"%(name)s\" or its tasks to copy.", name=self.name,
            )
        new_project.with_context(mail_post_autofollow=False).message_post(
            body=body, subtype_xmlid="mail.mt_note",
        )
