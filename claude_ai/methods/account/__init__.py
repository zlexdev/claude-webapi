"""Account-related endpoints."""

from claude_ai.methods.account.accept_legal_docs import AcceptLegalDocs
from claude_ai.methods.account.get_access import GetAccess
from claude_ai.methods.account.get_invites import GetInvites
from claude_ai.methods.account.get_profile import GetProfile
from claude_ai.methods.account.get_raven_eligible import GetRavenEligible
from claude_ai.methods.account.patch_settings import PatchAccountSettings
from claude_ai.methods.account.set_email_consent import SetEmailConsent
from claude_ai.methods.account.update_profile import UpdateProfile
from claude_ai.methods.account.update_settings import UpdateAccountSettings

__all__ = [
    "GetAccess",
    "GetProfile",
    "GetRavenEligible",
    "UpdateAccountSettings",
    "SetEmailConsent",
    "PatchAccountSettings",
    "AcceptLegalDocs",
    "UpdateProfile",
    "GetInvites",
]
