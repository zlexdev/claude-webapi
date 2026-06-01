"""Project (knowledge-base) endpoints."""

from claude_ai.methods.project.add_doc import AddDoc
from claude_ai.methods.project.get_conversations import GetProjectConversations
from claude_ai.methods.project.get_kb_stats import GetKBStats
from claude_ai.methods.project.get_members import GetMembers
from claude_ai.methods.project.get_permissions import GetPermissions
from claude_ai.methods.project.get_project import GetProject
from claude_ai.methods.project.list_docs import ListDocs
from claude_ai.methods.project.list_files import ListFiles
from claude_ai.methods.project.list_projects import ListProjects
from claude_ai.methods.project.sync_project import SyncProject
from claude_ai.methods.project.update_project import UpdateProject

__all__ = [
    "AddDoc",
    "GetKBStats",
    "GetMembers",
    "GetPermissions",
    "GetProject",
    "GetProjectConversations",
    "ListDocs",
    "ListFiles",
    "ListProjects",
    "SyncProject",
    "UpdateProject",
]
