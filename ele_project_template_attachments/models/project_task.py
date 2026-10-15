import logging

from odoo import models

_logger = logging.getLogger(__name__)


def _copy_attachments(env, source, target):
    """Create independent copies of the attachments linked directly to the
    record ``source`` and link them to ``target`` (same model). Returns count."""
    Attachment = env["ir.attachment"].sudo()
    attachments = Attachment.search([
        ("res_model", "=", source._name),
        ("res_id", "=", source.id),
        ("res_field", "=", False),  # skip binary-field storage / html images
    ])
    vals_list = []
    for att in attachments:
        vals = {
            "name": att.name,
            "description": att.description,
            "type": att.type,
            "mimetype": att.mimetype,
            "res_model": target._name,
            "res_id": target.id,
            "company_id": target.company_id.id or False,
        }
        if att.type == "url":
            vals["url"] = att.url
        else:
            vals["raw"] = att.raw or b""
        vals_list.append(vals)
    if vals_list:
        Attachment.create(vals_list)
    return len(vals_list)


class ProjectTask(models.Model):
    _inherit = "project.task"

    def copy(self, default=None):
        """Copy task attachments when a template is involved:
        - project -> template (Convert into template)
        - template -> project (Create project from template)
        - task template -> task
        Sub-tasks are handled too.
        """
        new_tasks = super().copy(default=default)

        ctx = self.env.context
        flow = bool(ctx.get("copy_from_template") or ctx.get("convert_to_template"))

        for source, new_task in self._template_copy_pairs(new_tasks):
            if flow or source._is_template_related() or new_task._is_template_related():
                n = _copy_attachments(self.env, source, new_task)
                if n:
                    _logger.info(
                        "ele_project_template_attachments: %s file(s) copied from task %s to task %s",
                        n, source.id, new_task.id,
                    )
        return new_tasks

    def _is_template_related(self):
        self.ensure_one()
        if "is_template" in self._fields and self.is_template:
            return True
        project = self.project_id
        return bool(project and "is_template" in project._fields and project.is_template)

    def _template_copy_pairs(self, copies):
        """Pair every original task (and its sub-tasks) with its copy."""
        pairs = []
        for original, copied in zip(self, copies):
            pairs.append((original, copied))
            orig_children = original.with_context(active_test=False).child_ids.filtered("active")
            new_children = copied.with_context(active_test=False).child_ids.sorted("id")
            if orig_children and len(orig_children) == len(new_children):
                pairs.extend(orig_children._template_copy_pairs(new_children))
        return pairs
