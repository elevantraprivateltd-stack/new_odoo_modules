{
    "name": "Ele Project Template Attachments",
    "version": "19.0.1.0.3",
    "category": "Services/Project",
    "summary": "Files attached to a project template are copied into every new project created from it",
    "description": """
Project Template Attachments
============================
When a project is created from a project template (or a template is duplicated),
all files attached directly to the template project are copied as independent
attachments into the new project.

* Project files AND task files (incl. sub-tasks) are copied
* Independent copies: deleting/renaming a copy never affects the template
* Works with Odoo 19 Community (depends only on project)
    """,
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["project"],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
