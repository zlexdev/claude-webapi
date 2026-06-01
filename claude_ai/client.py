"""ClaudeAIClient: thin facade. `await self(MethodCls(), params)` routes to session.{request,stream,multipart} based on method flags, then auto-binds results."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import TracebackType
from typing import Any

from claude_ai.bus.base import BaseEventBus
from claude_ai.config import ClaudeAISettings
from claude_ai.enums.auth import CredentialMethod, Locale, SourceApp
from claude_ai.enums.billing import BillingPlan, ConsentVariant, EligibilityCheck
from claude_ai.enums.status import BillingInterval
from claude_ai.methods.account.accept_legal_docs import AcceptLegalDocs
from claude_ai.methods.account.get_access import GetAccess, GetAccessParams
from claude_ai.methods.account.get_invites import GetInvites
from claude_ai.methods.account.get_profile import GetProfile
from claude_ai.methods.account.get_raven_eligible import GetRavenEligible
from claude_ai.methods.account.patch_settings import PatchAccountSettings
from claude_ai.methods.account.set_email_consent import SetEmailConsent
from claude_ai.methods.account.update_profile import UpdateProfile
from claude_ai.methods.account.update_settings import UpdateAccountSettings
from claude_ai.methods.artifact.download_file import (
    DownloadFile,
    DownloadFileParams,
)
from claude_ai.methods.artifact.get_versions import GetVersions, GetVersionsParams
from claude_ai.methods.artifact.upload_file import UploadFile, UploadFileParams
from claude_ai.methods.auth.exchange_nonce_for_code import ExchangeNonceForCode
from claude_ai.methods.auth.get_login_methods import GetLoginMethods
from claude_ai.methods.auth.send_magic_link import SendMagicLink
from claude_ai.methods.auth.verify_google import VerifyGoogle
from claude_ai.methods.auth.verify_magic_link import VerifyMagicLink
from claude_ai.methods.billing.create_stripe_intent import CreateStripeIntent
from claude_ai.methods.billing.get_consumer_pricing import GetConsumerPricing
from claude_ai.methods.billing.get_gift_eligibility import GetGiftEligibility
from claude_ai.methods.billing.get_plan_pricing import GetPlanPricing
from claude_ai.methods.billing.get_stripe_region import GetStripeRegion
from claude_ai.methods.bootstrap.get_app_start import GetAppStart
from claude_ai.methods.bootstrap.get_current_user_access import GetCurrentUserAccess
from claude_ai.methods.bootstrap.get_edge_bootstrap import GetEdgeBootstrap
from claude_ai.methods.bootstrap.get_mcp_bootstrap import GetMcpBootstrap
from claude_ai.methods.claude_code.get_user_settings import GetClaudeCodeSettings
from claude_ai.methods.claude_code.update_user_settings import (
    UpdateClaudeCodeSettings,
)
from claude_ai.methods.conversation.create_conversation import (
    CreateConversation,
    CreateConversationParams,
)
from claude_ai.methods.conversation.delete_conversation import (
    DeleteConversation,
    DeleteConversationParams,
)
from claude_ai.methods.conversation.delete_many import DeleteMany, DeleteManyParams
from claude_ai.methods.conversation.generate_title import (
    GenerateTitle,
    GenerateTitleParams,
)
from claude_ai.methods.conversation.get_conversation import (
    GetConversation,
    GetConversationParams,
)
from claude_ai.methods.conversation.list_conversations import (
    ListConversations,
    ListConversationsParams,
)
from claude_ai.methods.conversation.send_message import (
    SendMessage,
    SendMessageParams,
)
from claude_ai.methods.conversation.update_conversation import (
    UpdateConversation,
    UpdateConversationParams,
)
from claude_ai.methods.misc.check_team_signup_eligibility import (
    CheckTeamSignupEligibility,
)
from claude_ai.methods.misc.check_team_trial_eligibility import (
    CheckTeamTrialEligibility,
)
from claude_ai.methods.misc.get_referral import GetReferral
from claude_ai.methods.organization.get_cowork_settings import GetCoworkSettings
from claude_ai.methods.organization.get_credits import GetCredits, GetCreditsParams
from claude_ai.methods.organization.get_experiences import GetExperiences
from claude_ai.methods.organization.get_memory import GetMemory, GetMemoryParams
from claude_ai.methods.organization.get_memory_settings import GetMemorySettings
from claude_ai.methods.organization.get_model_config import (
    GetModelConfig,
    GetModelConfigParams,
)
from claude_ai.methods.organization.get_notification_preferences import (
    GetNotificationPreferences,
)
from claude_ai.methods.organization.get_organization import (
    GetOrganization,
    GetOrganizationParams,
)
from claude_ai.methods.organization.get_overage_spend_limit import (
    GetOverageSpendLimit,
)
from claude_ai.methods.organization.get_paused_subscription import (
    GetPausedSubscription,
)
from claude_ai.methods.organization.get_payment_method import GetPaymentMethod
from claude_ai.methods.organization.get_pending_domain_claim import (
    GetPendingDomainClaim,
)
from claude_ai.methods.organization.get_styles import GetStyles, GetStylesParams
from claude_ai.methods.organization.get_subscription import (
    GetSubscription,
    GetSubscriptionParams,
)
from claude_ai.methods.organization.list_discoverable import ListDiscoverable
from claude_ai.methods.organization.list_marketplaces import ListMarketplaces
from claude_ai.methods.organization.list_skills import ListSkills
from claude_ai.methods.project.add_doc import AddDoc, AddDocParams
from claude_ai.methods.project.get_conversations import (
    GetProjectConversations,
    GetProjectConversationsParams,
)
from claude_ai.methods.project.get_kb_stats import GetKBStats, GetKBStatsParams
from claude_ai.methods.project.get_members import GetMembers, GetMembersParams
from claude_ai.methods.project.get_permissions import (
    GetPermissions,
    GetPermissionsParams,
)
from claude_ai.methods.project.get_project import GetProject, GetProjectParams
from claude_ai.methods.project.list_docs import ListDocs, ListDocsParams
from claude_ai.methods.project.list_files import ListFiles, ListFilesParams
from claude_ai.methods.project.list_projects import ListProjects, ListProjectsParams
from claude_ai.methods.project.sync_project import SyncProject, SyncProjectParams
from claude_ai.methods.project.update_project import (
    UpdateProject,
    UpdateProjectParams,
)
from claude_ai.methods.sync.get_auth_status import (
    GetSyncAuthStatus,
    GetSyncAuthStatusParams,
)
from claude_ai.methods.sync.get_sync_settings import (
    GetSyncSettings,
    GetSyncSettingsParams,
)
from claude_ai.models._object import ClaudeObject
from claude_ai.models.account import AccessInfo, AccountProfile
from claude_ai.models.artifact import ArtifactVersion, WiggleUploadResult
from claude_ai.models.auth import AuthResult, LoginMethods, MagicLinkResult
from claude_ai.models.billing import (
    ConsumerPricing,
    Eligibility,
    PausedSubscription,
    StripeIntent,
    StripeRegion,
)
from claude_ai.models.bootstrap import CurrentUserAccess
from claude_ai.models.conversation import Conversation
from claude_ai.models.organization import (
    Credits,
    Memory,
    ModelConfig,
    Organization,
    PaymentMethod,
    Style,
    SubscriptionDetails,
)
from claude_ai.models.pagination import PaginatedResponse
from claude_ai.models.project import (
    KBStats,
    Project,
    ProjectDoc,
    ProjectFile,
    ProjectPermissions,
)
from claude_ai.models.settings import (
    CoworkSettings,
    DiscoverableOrgs,
    MarketplaceList,
    MemorySettings,
    SkillList,
    UserSettingsWriteResult,
)
from claude_ai.models.streaming import StreamEvent
from claude_ai.models.sync import SyncAuth, SyncSettings
from claude_ai.session.base import BaseSession
from claude_ai.session.http import HttpSession
from claude_ai.storage.cache.base import BaseCache, CacheNamespace
from claude_ai.streaming.collector import CompletionResult, StreamCollector


class ClaudeAIClient:
    def __init__(
        self,
        account_id: str = "default",
        *,
        session: BaseSession | None = None,
        settings: ClaudeAISettings | None = None,
        org_uuid: str | None = None,
        bus: BaseEventBus | None = None,
        cache: BaseCache | None = None,
    ) -> None:
        self.account_id = account_id
        self._settings = settings or ClaudeAISettings()
        self._session = session or HttpSession(
            account_id=account_id, settings=self._settings, bus=bus
        )
        self._org_uuid = org_uuid or ""
        self.cache = cache
        self._bus = bus

    @property
    def session(self) -> BaseSession:
        return self._session

    @property
    def bus(self) -> BaseEventBus | None:
        return self._bus

    @bus.setter
    def bus(self, value: BaseEventBus | None) -> None:
        self._bus = value
        if isinstance(self._session, HttpSession):
            self._session._bus = value  # type: ignore[attr-defined]

    @property
    def org_uuid(self) -> str:
        return self._org_uuid

    @org_uuid.setter
    def org_uuid(self, value: str) -> None:
        self._org_uuid = value

    def _require_org(self) -> str:
        if not self._org_uuid:
            raise ValueError(
                "org_uuid is required — set client.org_uuid or pass org_uuid param"
            )
        return self._org_uuid

    async def open(self) -> None:
        await self._session.open()

    async def close(self) -> None:
        await self._session.close()

    async def __aenter__(self) -> ClaudeAIClient:
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def __call__(self, method: Any, params: Any = None) -> Any:
        if getattr(method, "__is_stream__", False):
            return await self._session.stream(method, params)
        if getattr(method, "__is_multipart__", False):
            result = await self._session.multipart(method, params)
        else:
            result = await self._session.request(method, params)
        return self._bind(result)

    def _bind(self, value: Any) -> Any:
        """Recursively bind any ClaudeObject in the result to this client.

        Centralised here so call sites never repeat it. Handles bare objects,
        `PaginatedResponse.data`, and plain lists of objects; passes dicts /
        scalars / None straight through.
        """
        if isinstance(value, ClaudeObject):
            value.bind(self)
        elif isinstance(value, PaginatedResponse):
            for item in value.data:
                self._bind(item)
        elif isinstance(value, list):
            for item in value:
                self._bind(item)
        return value

    async def _cache_get(self, ns: CacheNamespace, key: str) -> Any | None:
        if self.cache is None:
            return None
        return await self.cache.get(ns, key)

    async def _cache_set(self, ns: CacheNamespace, key: str, value: Any) -> None:
        if self.cache is None:
            return
        if hasattr(value, "model_dump"):
            await self.cache.set(ns, key, value.model_dump(mode="json"))
        else:
            await self.cache.set(ns, key, value)


    async def get_login_methods(
        self, email: str, source: SourceApp = SourceApp.CLAUDE
    ) -> LoginMethods:
        return await self(GetLoginMethods(email=email, source=source))

    async def send_magic_link(
        self,
        email_address: str,
        locale: Locale = Locale.EN_US,
        source: SourceApp = SourceApp.CLAUDE,
        utc_offset: int = 0,
        login_intent: str | None = None,
        return_to: str | None = None,
    ) -> MagicLinkResult:
        return await self(
            SendMagicLink(
                email_address=email_address,
                locale=locale,
                source=source,
                utc_offset=utc_offset,
                login_intent=login_intent,
                return_to=return_to,
            )
        )

    async def verify_magic_link(
        self,
        nonce: str | None = None,
        encoded_email_address: str | None = None,
        code: str | None = None,
        method: CredentialMethod = CredentialMethod.NONCE,
        locale: Locale = Locale.EN_US,
        source: SourceApp = SourceApp.CLAUDE,
    ) -> AuthResult:
        return await self(
            VerifyMagicLink(
                method=method,
                nonce=nonce,
                encoded_email_address=encoded_email_address,
                code=code,
                locale=locale,
                source=source,
            )
        )

    async def exchange_nonce_for_code(
        self,
        nonce: str,
        encoded_email_address: str | None = None,
        method: CredentialMethod = CredentialMethod.NONCE,
        locale: Locale = Locale.EN_US,
        source: SourceApp = SourceApp.CLAUDE,
    ) -> AuthResult:
        return await self(
            ExchangeNonceForCode(
                nonce=nonce,
                encoded_email_address=encoded_email_address,
                method=method,
                locale=locale,
                source=source,
            )
        )

    async def verify_google(
        self,
        code: str,
        arkose_session_token: str,
        locale: Locale = Locale.EN_US,
        source: SourceApp = SourceApp.CLAUDE,
        return_to: str | None = None,
    ) -> None:
        await self(
            VerifyGoogle(
                code=code,
                arkose_session_token=arkose_session_token,
                locale=locale,
                source=source,
                return_to=return_to,
            )
        )


    async def get_profile(self) -> AccountProfile:
        return await self(GetProfile())

    async def get_access(self, org_uuid: str | None = None) -> AccessInfo:
        return await self(
            GetAccess(), GetAccessParams(org_uuid=org_uuid or self._require_org())
        )

    async def get_raven_eligible(self) -> dict[str, Any]:
        return await self(GetRavenEligible())

    async def update_account_settings(
        self, settings: dict[str, Any]
    ) -> dict[str, Any]:
        return await self(UpdateAccountSettings(settings=settings))

    async def set_email_consent(
        self,
        consent: bool = True,
        accepted_via_checkbox: bool = True,
        variant: ConsentVariant = ConsentVariant.NOTICES,
    ) -> None:
        await self(
            SetEmailConsent(
                consent=consent,
                accepted_via_checkbox=accepted_via_checkbox,
                variant=variant,
            )
        )

    async def patch_account_settings(self, settings: dict[str, Any]) -> None:
        await self(PatchAccountSettings(settings=settings))

    async def accept_legal_docs(self, acceptances: list[dict[str, Any]]) -> None:
        await self(AcceptLegalDocs(acceptances=acceptances))

    async def update_profile(
        self,
        work_function: str | None = None,
        locale: str | None = None,
        conversation_preferences: str | None = None,
    ) -> AccountProfile:
        return await self(
            UpdateProfile(
                work_function=work_function,
                locale=locale,
                conversation_preferences=conversation_preferences,
            )
        )

    async def get_invites(self, account_uuid: str) -> list[Any]:
        return await self(GetInvites(account_uuid=account_uuid))


    async def get_organization(self, org_uuid: str | None = None) -> Organization:
        return await self(
            GetOrganization(),
            GetOrganizationParams(org_uuid=org_uuid or self._require_org()),
        )

    async def get_subscription(
        self, org_uuid: str | None = None
    ) -> SubscriptionDetails:
        return await self(
            GetSubscription(),
            GetSubscriptionParams(org_uuid=org_uuid or self._require_org()),
        )

    async def get_model_config(
        self, model_id: str, org_uuid: str | None = None
    ) -> ModelConfig:
        return await self(
            GetModelConfig(),
            GetModelConfigParams(
                org_uuid=org_uuid or self._require_org(), model_id=model_id
            ),
        )

    async def get_credits(self, org_uuid: str | None = None) -> Credits:
        return await self(
            GetCredits(), GetCreditsParams(org_uuid=org_uuid or self._require_org())
        )

    async def get_styles(self, org_uuid: str | None = None) -> list[Style]:
        return await self(
            GetStyles(), GetStylesParams(org_uuid=org_uuid or self._require_org())
        )

    async def get_memory(
        self, project_uuid: str | None = None, org_uuid: str | None = None
    ) -> Memory:
        return await self(
            GetMemory(),
            GetMemoryParams(
                org_uuid=org_uuid or self._require_org(), project_uuid=project_uuid
            ),
        )

    async def get_payment_method(
        self, org_uuid: str | None = None
    ) -> PaymentMethod | None:
        return await self(
            GetPaymentMethod(org_uuid=org_uuid or self._require_org())
        )

    async def get_paused_subscription(
        self, org_uuid: str | None = None
    ) -> PausedSubscription | None:
        return await self(
            GetPausedSubscription(org_uuid=org_uuid or self._require_org())
        )

    async def list_discoverable_organizations(self) -> DiscoverableOrgs:
        return await self(ListDiscoverable())

    async def get_cowork_settings(
        self, org_uuid: str | None = None
    ) -> CoworkSettings:
        return await self(
            GetCoworkSettings(org_uuid=org_uuid or self._require_org())
        )

    async def get_experiences(
        self, locale: Locale = Locale.EN_US, org_uuid: str | None = None
    ) -> dict[str, Any]:
        return await self(
            GetExperiences(org_uuid=org_uuid or self._require_org(), locale=locale)
        )

    async def list_marketplaces(
        self, org_uuid: str | None = None
    ) -> MarketplaceList:
        return await self(
            ListMarketplaces(org_uuid=org_uuid or self._require_org())
        )

    async def get_memory_settings(
        self, org_uuid: str | None = None
    ) -> MemorySettings:
        return await self(
            GetMemorySettings(org_uuid=org_uuid or self._require_org())
        )

    async def get_notification_preferences(
        self, org_uuid: str | None = None
    ) -> dict[str, Any]:
        return await self(
            GetNotificationPreferences(org_uuid=org_uuid or self._require_org())
        )

    async def list_skills(self, org_uuid: str | None = None) -> SkillList:
        return await self(ListSkills(org_uuid=org_uuid or self._require_org()))

    async def get_overage_spend_limit(
        self, org_uuid: str | None = None
    ) -> dict[str, Any] | None:
        return await self(
            GetOverageSpendLimit(org_uuid=org_uuid or self._require_org())
        )

    async def get_pending_domain_claim(
        self, org_uuid: str | None = None
    ) -> dict[str, Any] | None:
        return await self(
            GetPendingDomainClaim(org_uuid=org_uuid or self._require_org())
        )


    async def get_stripe_region(
        self, country: str, organization_uuid: str | None = None
    ) -> StripeRegion:
        return await self(
            GetStripeRegion(
                country=country,
                organization_uuid=organization_uuid or self._require_org(),
            )
        )

    async def get_gift_eligibility(
        self, org_uuid: str | None = None
    ) -> Eligibility:
        return await self(
            GetGiftEligibility(org_uuid=org_uuid or self._require_org())
        )

    async def get_consumer_pricing(
        self,
        country: str,
        billing_interval: BillingInterval = BillingInterval.MONTHLY,
        org_uuid: str | None = None,
    ) -> ConsumerPricing:
        return await self(
            GetConsumerPricing(
                org_uuid=org_uuid or self._require_org(),
                country=country,
                billing_interval=billing_interval,
            )
        )

    async def get_plan_pricing(
        self, country: str, org_uuid: str | None = None
    ) -> dict[str, Any]:
        return await self(
            GetPlanPricing(org_uuid=org_uuid or self._require_org(), country=country)
        )

    async def create_stripe_intent(
        self,
        plan: BillingPlan,
        country: str,
        billing_address: dict[str, Any] | None = None,
        org_uuid: str | None = None,
    ) -> StripeIntent:
        return await self(
            CreateStripeIntent(
                org_uuid=org_uuid or self._require_org(),
                plan=plan,
                country=country,
                billing_address=billing_address,
            )
        )


    async def get_claude_code_settings(
        self, org_uuid: str | None = None
    ) -> dict[str, Any]:
        return await self(
            GetClaudeCodeSettings(org_uuid=org_uuid or self._require_org())
        )

    async def update_claude_code_settings(
        self, entries: dict[str, str], org_uuid: str | None = None
    ) -> UserSettingsWriteResult:
        return await self(
            UpdateClaudeCodeSettings(
                org_uuid=org_uuid or self._require_org(), entries=entries
            )
        )


    async def get_current_user_access(
        self, org_uuid: str | None = None
    ) -> CurrentUserAccess:
        return await self(
            GetCurrentUserAccess(org_uuid=org_uuid or self._require_org())
        )

    async def get_mcp_bootstrap(self, org_uuid: str | None = None) -> dict[str, Any]:
        return await self(
            GetMcpBootstrap(org_uuid=org_uuid or self._require_org())
        )

    async def get_edge_bootstrap(
        self, include_system_prompts: bool = False
    ) -> dict[str, Any]:
        return await self(
            GetEdgeBootstrap(include_system_prompts=include_system_prompts)
        )

    async def get_app_start(
        self, org_uuid: str | None = None, include_system_prompts: bool = False
    ) -> dict[str, Any]:
        return await self(
            GetAppStart(
                org_uuid=org_uuid or self._require_org(),
                include_system_prompts=include_system_prompts,
            )
        )


    async def get_referral(self) -> dict[str, Any] | None:
        return await self(GetReferral())

    async def check_team_signup_eligibility(
        self, check: EligibilityCheck = EligibilityCheck.TEAM_VOUCHER
    ) -> Eligibility:
        return await self(CheckTeamSignupEligibility(check=check))

    async def check_team_trial_eligibility(
        self, check: EligibilityCheck = EligibilityCheck.TEAM_TRIAL_EXPOSURE
    ) -> Eligibility:
        return await self(CheckTeamTrialEligibility(check=check))


    async def list_conversations(
        self,
        limit: int = 50,
        starred: bool | None = None,
        org_uuid: str | None = None,
    ) -> PaginatedResponse[Conversation]:
        cache_key = f"{org_uuid or self._org_uuid}:{limit}:{starred}"
        cached = await self._cache_get(CacheNamespace.CONVERSATION_LIST, cache_key)
        if cached is not None:
            return self._bind(PaginatedResponse[Conversation].model_validate(cached))
        result = await self(
            ListConversations(),
            ListConversationsParams(
                org_uuid=org_uuid or self._require_org(), limit=limit, starred=starred
            ),
        )
        await self._cache_set(CacheNamespace.CONVERSATION_LIST, cache_key, result)
        return result

    async def get_conversation(
        self, conv_uuid: str, tree: bool = True, org_uuid: str | None = None
    ) -> Conversation:
        cached = await self._cache_get(CacheNamespace.CONVERSATION, conv_uuid)
        if cached is not None:
            return self._bind(Conversation.model_validate(cached))
        result = await self(
            GetConversation(),
            GetConversationParams(
                org_uuid=org_uuid or self._require_org(), conv_uuid=conv_uuid, tree=tree
            ),
        )
        await self._cache_set(CacheNamespace.CONVERSATION, conv_uuid, result)
        return result

    async def create_conversation(
        self,
        uuid: str,
        name: str = "",
        model: str | None = None,
        is_temporary: bool = False,
        org_uuid: str | None = None,
    ) -> Conversation:
        result = await self(
            CreateConversation(),
            CreateConversationParams(
                org_uuid=org_uuid or self._require_org(),
                uuid=uuid,
                name=name,
                model=model or self._settings.default_model,
                is_temporary=is_temporary,
            ),
        )
        await self._cache_set(CacheNamespace.CONVERSATION, uuid, result)
        return result

    async def create_conversation_for_prompt(self, _prompt: str) -> Conversation:
        import uuid as uuid_lib

        new_uuid = str(uuid_lib.uuid4())
        return await self.create_conversation(uuid=new_uuid)

    async def update_conversation(
        self,
        conv_uuid: str,
        name: str | None = None,
        project_uuid: str | None = None,
        org_uuid: str | None = None,
    ) -> None:
        await self(
            UpdateConversation(),
            UpdateConversationParams(
                org_uuid=org_uuid or self._require_org(),
                conv_uuid=conv_uuid,
                name=name,
                project_uuid=project_uuid,
            ),
        )
        if self.cache is not None:
            await self.cache.delete(CacheNamespace.CONVERSATION, conv_uuid)

    async def delete_conversation(
        self, conv_uuid: str, org_uuid: str | None = None
    ) -> None:
        await self(
            DeleteConversation(),
            DeleteConversationParams(
                org_uuid=org_uuid or self._require_org(), conv_uuid=conv_uuid
            ),
        )
        if self.cache is not None:
            await self.cache.delete(CacheNamespace.CONVERSATION, conv_uuid)

    async def delete_conversations(
        self, conv_uuids: list[str], org_uuid: str | None = None
    ) -> None:
        await self(
            DeleteMany(),
            DeleteManyParams(
                org_uuid=org_uuid or self._require_org(), conversation_uuids=conv_uuids
            ),
        )
        if self.cache is not None:
            for cu in conv_uuids:
                await self.cache.delete(CacheNamespace.CONVERSATION, cu)

    async def generate_title(
        self,
        conv_uuid: str,
        message_content: str = "",
        recent_titles: list[str] | None = None,
        org_uuid: str | None = None,
    ) -> str:
        return await self(
            GenerateTitle(),
            GenerateTitleParams(
                org_uuid=org_uuid or self._require_org(),
                conv_uuid=conv_uuid,
                message_content=message_content,
                recent_titles=recent_titles,
            ),
        )

    async def send_message(
        self,
        conv_uuid: str,
        prompt: str,
        model: str | None = None,
        org_uuid: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        params = SendMessageParams(
            org_uuid=org_uuid or self._require_org(),
            conv_uuid=conv_uuid,
            prompt=prompt,
            model=model or self._settings.default_model,
            timezone=self._settings.timezone,
            locale=self._settings.locale,
            **kwargs,
        )
        return await self(SendMessage(), params)

    async def send_message_and_collect(
        self,
        conv_uuid: str,
        prompt: str,
        model: str | None = None,
        org_uuid: str | None = None,
        **kwargs: Any,
    ) -> CompletionResult:
        events = await self.send_message(conv_uuid, prompt, model, org_uuid, **kwargs)
        return await StreamCollector(events).collect()


    async def list_projects(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "updated_at",
        search_query: str | None = None,
        org_uuid: str | None = None,
    ) -> PaginatedResponse[Project]:
        return await self(
            ListProjects(),
            ListProjectsParams(
                org_uuid=org_uuid or self._require_org(),
                limit=limit,
                offset=offset,
                order_by=order_by,
                search_query=search_query,
            ),
        )

    async def get_project(
        self, project_uuid: str, org_uuid: str | None = None
    ) -> Project:
        cached = await self._cache_get(CacheNamespace.PROJECT, project_uuid)
        if cached is not None:
            return self._bind(Project.model_validate(cached))
        result = await self(
            GetProject(),
            GetProjectParams(
                org_uuid=org_uuid or self._require_org(), project_uuid=project_uuid
            ),
        )
        await self._cache_set(CacheNamespace.PROJECT, project_uuid, result)
        return result

    async def update_project(
        self,
        project_uuid: str,
        name: str | None = None,
        description: str | None = None,
        org_uuid: str | None = None,
    ) -> None:
        await self(
            UpdateProject(),
            UpdateProjectParams(
                org_uuid=org_uuid or self._require_org(),
                project_uuid=project_uuid,
                name=name,
                description=description,
            ),
        )
        if self.cache is not None:
            await self.cache.delete(CacheNamespace.PROJECT, project_uuid)

    async def get_project_members(
        self, project_uuid: str, org_uuid: str | None = None
    ) -> list[Any]:
        return await self(
            GetMembers(),
            GetMembersParams(
                org_uuid=org_uuid or self._require_org(), project_uuid=project_uuid
            ),
        )

    async def get_project_permissions(
        self, project_uuid: str, org_uuid: str | None = None
    ) -> ProjectPermissions:
        return await self(
            GetPermissions(),
            GetPermissionsParams(
                org_uuid=org_uuid or self._require_org(), project_uuid=project_uuid
            ),
        )

    async def list_project_docs(
        self, project_uuid: str, org_uuid: str | None = None
    ) -> list[ProjectDoc]:
        return await self(
            ListDocs(),
            ListDocsParams(
                org_uuid=org_uuid or self._require_org(), project_uuid=project_uuid
            ),
        )

    async def add_project_doc(
        self,
        project_uuid: str,
        file_name: str,
        content: str,
        org_uuid: str | None = None,
    ) -> ProjectDoc:
        return await self(
            AddDoc(),
            AddDocParams(
                org_uuid=org_uuid or self._require_org(),
                project_uuid=project_uuid,
                file_name=file_name,
                content=content,
            ),
        )

    async def list_project_files(
        self, project_uuid: str, org_uuid: str | None = None
    ) -> list[ProjectFile]:
        return await self(
            ListFiles(),
            ListFilesParams(
                org_uuid=org_uuid or self._require_org(), project_uuid=project_uuid
            ),
        )

    async def get_project_conversations(
        self,
        project_uuid: str,
        limit: int = 50,
        offset: int = 0,
        org_uuid: str | None = None,
    ) -> PaginatedResponse[Conversation]:
        return await self(
            GetProjectConversations(),
            GetProjectConversationsParams(
                org_uuid=org_uuid or self._require_org(),
                project_uuid=project_uuid,
                limit=limit,
                offset=offset,
            ),
        )

    async def get_kb_stats(
        self, project_uuid: str, org_uuid: str | None = None
    ) -> KBStats:
        return await self(
            GetKBStats(),
            GetKBStatsParams(
                org_uuid=org_uuid or self._require_org(), project_uuid=project_uuid
            ),
        )

    async def sync_project(
        self, project_uuid: str, org_uuid: str | None = None
    ) -> None:
        await self(
            SyncProject(),
            SyncProjectParams(
                org_uuid=org_uuid or self._require_org(), project_uuid=project_uuid
            ),
        )


    async def get_artifact_versions(
        self,
        conv_uuid: str,
        source: str | None = None,
        org_uuid: str | None = None,
    ) -> list[ArtifactVersion]:
        return await self(
            GetVersions(),
            GetVersionsParams(
                org_uuid=org_uuid or self._require_org(),
                conv_uuid=conv_uuid,
                source=source,
            ),
        )

    async def upload_file(
        self,
        conv_uuid: str,
        file_content: bytes,
        file_name: str,
        org_uuid: str | None = None,
    ) -> WiggleUploadResult:
        params = UploadFileParams(
            org_uuid=org_uuid or self._require_org(),
            conv_uuid=conv_uuid,
            file_content=file_content,
            file_name=file_name,
        )
        return await self(UploadFile(), params)

    async def download_file(
        self, conv_uuid: str, path: str, org_uuid: str | None = None
    ) -> bytes:
        return await self(
            DownloadFile(),
            DownloadFileParams(
                org_uuid=org_uuid or self._require_org(),
                conv_uuid=conv_uuid,
                path=path,
            ),
        )


    async def get_sync_settings(self, org_uuid: str | None = None) -> SyncSettings:
        return await self(
            GetSyncSettings(),
            GetSyncSettingsParams(org_uuid=org_uuid or self._require_org()),
        )

    async def get_sync_auth_status(
        self, provider: str, org_uuid: str | None = None
    ) -> SyncAuth:
        return await self(
            GetSyncAuthStatus(),
            GetSyncAuthStatusParams(
                org_uuid=org_uuid or self._require_org(), provider=provider
            ),
        )
