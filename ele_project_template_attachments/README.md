# Project Template Attachments (Odoo 19 Community)

Files attached to a project or to its tasks (and sub-tasks) are copied as
independent copies when:
- a project is converted into a template,
- a new project is created from a template,
- a template is duplicated.

## Install / Update
1. Put the folder project_template_attachments in your custom addons path.
2. RESTART the Odoo server (needed for Python changes).
3. Apps -> Update Apps List -> Install (or Upgrade if already installed).

After each copy a note is posted in the chatter of the new project:
"Files copied from ...: X project file(s), Y task file(s)."
Existing projects/templates are not changed: re-create the template.
