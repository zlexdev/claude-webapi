# SDK Methods — generic dispatch reference

Auto-generated from the `claude_ai.methods` classes. Call any method via:

```
POST /v1/methods/invoke
{ "method": "<name>", "account_id": "<acc>", "params": { ... } }
```

## account

### AcceptLegalDocs
- `PUT /api/account/accept_legal_docs` → `NoneType`
- style: `field`
- params: `["acceptances"]`

### GetAccess
- `GET /api/organizations/{org_uuid}/my-access` → `AccessInfo`
- style: `legacy`

### GetInvites
- `GET /api/accounts/{account_uuid}/invites` → `list`
- style: `field`
- params: `["account_uuid"]`

### GetProfile
- `GET /api/account_profile` → `AccountProfile`
- style: `legacy`

### GetRavenEligible
- `GET /api/account/raven_eligible` → `dict`
- style: `legacy`

### PatchAccountSettings
- `PATCH /api/account/settings` → `NoneType`
- style: `field`
- params: `["settings"]`

### SetEmailConsent
- `PUT /api/account/email_consent` → `NoneType`
- style: `field`
- params: `["accepted_via_checkbox", "consent", "variant"]`

### UpdateAccountSettings
- `PUT /api/account` → `dict`
- style: `field`
- params: `["settings"]`

### UpdateProfile
- `PUT /api/account_profile` → `AccountProfile`
- style: `field`
- params: `["conversation_preferences", "locale", "work_function"]`

## artifact

### DownloadFile
- `GET /api/organizations/{org_uuid}/conversations/{conv_uuid}/wiggle/download-file` → `bytes`
- style: `legacy`

### GetVersions
- `GET /api/organizations/{org_uuid}/artifacts/{conv_uuid}/versions` → `list`
- style: `legacy`

### UploadFile · multipart (not dispatchable)
- `POST /api/organizations/{org_uuid}/conversations/{conv_uuid}/wiggle/upload-file` → `WiggleUploadResult`
- style: `legacy`

## auth

### ExchangeNonceForCode
- `POST /api/auth/exchange_nonce_for_code` → `AuthResult`
- style: `field`
- params: `["encoded_email_address", "locale", "method", "nonce", "source"]`

### GetLoginMethods
- `GET /api/auth/login_methods` → `LoginMethods`
- style: `field`
- params: `["email", "source"]`

### SendMagicLink
- `POST /api/auth/send_magic_link` → `MagicLinkResult`
- style: `field`
- params: `["email_address", "locale", "login_intent", "return_to", "source", "utc_offset"]`

### VerifyGoogle
- `POST /api/auth/verify_google` → `NoneType`
- style: `field`
- params: `["arkose_session_token", "code", "locale", "return_to", "source"]`

### VerifyMagicLink
- `POST /api/auth/verify_magic_link` → `AuthResult`
- style: `field`
- params: `["code", "encoded_email_address", "locale", "method", "nonce", "source"]`

## billing

### CreateStripeIntent
- `POST /api/stripe/{org_uuid}/intent` → `StripeIntent`
- style: `field`
- params: `["billing_address", "country", "org_uuid", "plan"]`

### GetConsumerPricing
- `POST /api/billing/{org_uuid}/consumer_pricing` → `ConsumerPricing`
- style: `field`
- params: `["billing_interval", "country", "org_uuid"]`

### GetGiftEligibility
- `GET /api/billing/{org_uuid}/gift/purchase_eligibility` → `Eligibility`
- style: `field`
- params: `["org_uuid"]`

### GetPlanPricing
- `POST /api/billing/{org_uuid}/individual_plan_pricing/v2` → `dict`
- style: `field`
- params: `["country", "org_uuid"]`

### GetStripeRegion
- `GET /api/billing/stripe_region` → `StripeRegion`
- style: `field`
- params: `["country", "organization_uuid"]`

## bootstrap

### GetAppStart
- `GET /edge-api/bootstrap/{org_uuid}/app_start` → `dict`
- style: `field`
- params: `["include_system_prompts", "org_uuid"]`

### GetCurrentUserAccess
- `GET /api/bootstrap/{org_uuid}/current_user_access` → `CurrentUserAccess`
- style: `field`
- params: `["org_uuid"]`

### GetEdgeBootstrap
- `GET /edge-api/bootstrap` → `dict`
- style: `field`
- params: `["include_system_prompts"]`

### GetMcpBootstrap
- `GET /api/organizations/{org_uuid}/mcp/v2/bootstrap` → `dict`
- style: `field`
- params: `["org_uuid"]`

## claude_code

### GetClaudeCodeSettings
- `GET /api/claude_code/organizations/{org_uuid}/user_settings` → `dict`
- style: `field`
- params: `["org_uuid"]`

### UpdateClaudeCodeSettings
- `PUT /api/claude_code/organizations/{org_uuid}/user_settings` → `UserSettingsWriteResult`
- style: `field`
- params: `["entries", "org_uuid"]`

## conversation

### CreateConversation
- `POST /api/organizations/{org_uuid}/chat_conversations` → `Conversation`
- style: `legacy`
- params: `["include_conversation_preferences", "is_temporary", "model", "name", "org_uuid", "uuid"]`

### DeleteConversation
- `DELETE /api/organizations/{org_uuid}/chat_conversations/{conv_uuid}` → `NoneType`
- style: `legacy`
- params: `["conv_uuid", "org_uuid"]`

### DeleteMany
- `POST /api/organizations/{org_uuid}/chat_conversations/delete_many` → `NoneType`
- style: `legacy`
- params: `["conversation_uuids", "org_uuid"]`

### GenerateTitle
- `POST /api/organizations/{org_uuid}/chat_conversations/{conv_uuid}/title` → `str`
- style: `legacy`
- params: `["conv_uuid", "message_content", "org_uuid", "recent_titles"]`

### GetConversation
- `GET /api/organizations/{org_uuid}/chat_conversations/{conv_uuid}` → `Conversation`
- style: `legacy`
- params: `["consistency", "conv_uuid", "org_uuid", "render_all_tools", "rendering_mode", "tree"]`

### ListConversations
- `GET /api/organizations/{org_uuid}/chat_conversations_v2` → `PaginatedResponse`
- style: `legacy`
- params: `["consistency", "limit", "org_uuid", "starred"]`

### SendMessage · stream
- `POST /api/organizations/{org_uuid}/chat_conversations/{conv_uuid}/completion` → `dict`
- style: `legacy`
- params: `["assistant_message_uuid", "attachments", "conv_uuid", "files", "human_message_uuid", "locale", "model", "org_uuid", "personalized_styles", "prompt", "rendering_mode", "sync_sources", "timezone", "tools"]`

### UpdateConversation
- `PUT /api/organizations/{org_uuid}/chat_conversations/{conv_uuid}` → `NoneType`
- style: `legacy`
- params: `["conv_uuid", "name", "org_uuid", "project_uuid"]`

## misc

### CheckTeamSignupEligibility
- `GET /api/team-signup/{check}` → `Eligibility`
- style: `field`
- params: `["check"]`

### CheckTeamTrialEligibility
- `GET /api/team-trial/{check}` → `Eligibility`
- style: `field`
- params: `["check"]`

### GetReferral
- `GET /api/referral` → `dict`
- style: `field`

## organization

### GetCoworkSettings
- `GET /api/organizations/{org_uuid}/cowork_settings` → `CoworkSettings`
- style: `field`
- params: `["org_uuid"]`

### GetCredits
- `GET /api/organizations/{org_uuid}/prepaid/credits` → `Credits`
- style: `legacy`

### GetExperiences
- `GET /api/organizations/{org_uuid}/experiences/claude_web` → `dict`
- style: `field`
- params: `["locale", "org_uuid"]`

### GetMemory
- `GET /api/organizations/{org_uuid}/memory` → `Memory`
- style: `legacy`

### GetMemorySettings
- `GET /api/organizations/{org_uuid}/memory/settings` → `MemorySettings`
- style: `field`
- params: `["org_uuid"]`

### GetModelConfig
- `GET /api/organizations/{org_uuid}/model_configs/{model_id}` → `ModelConfig`
- style: `legacy`

### GetNotificationPreferences
- `GET /api/organizations/{org_uuid}/notification/preferences` → `dict`
- style: `field`
- params: `["org_uuid"]`

### GetOrganization
- `GET /api/organizations/{org_uuid}` → `Organization`
- style: `legacy`

### GetOverageSpendLimit
- `GET /api/organizations/{org_uuid}/overage_spend_limit` → `dict`
- style: `field`
- params: `["org_uuid"]`

### GetPausedSubscription
- `GET /api/organizations/{org_uuid}/paused_subscription_details` → `PausedSubscription`
- style: `field`
- params: `["org_uuid"]`

### GetPaymentMethod
- `GET /api/organizations/{org_uuid}/payment_method` → `PaymentMethod`
- style: `field`
- params: `["org_uuid"]`

### GetPendingDomainClaim
- `GET /api/organizations/{org_uuid}/pending_domain_claim` → `dict`
- style: `field`
- params: `["org_uuid"]`

### GetStyles
- `GET /api/organizations/{org_uuid}/list_styles` → `list`
- style: `legacy`

### GetSubscription
- `GET /api/organizations/{org_uuid}/subscription_details` → `SubscriptionDetails`
- style: `legacy`

### ListDiscoverable
- `GET /api/organizations/discoverable` → `DiscoverableOrgs`
- style: `field`

### ListMarketplaces
- `GET /api/organizations/{org_uuid}/marketplaces/list-default-marketplaces` → `MarketplaceList`
- style: `field`
- params: `["org_uuid"]`

### ListSkills
- `GET /api/organizations/{org_uuid}/skills/list-skills` → `SkillList`
- style: `field`
- params: `["org_uuid"]`

## project

### AddDoc
- `POST /api/organizations/{org_uuid}/projects/{project_uuid}/docs` → `ProjectDoc`
- style: `legacy`

### GetKBStats
- `GET /api/organizations/{org_uuid}/projects/{project_uuid}/kb/stats` → `KBStats`
- style: `legacy`

### GetMembers
- `GET /api/organizations/{org_uuid}/projects/{project_uuid}/accounts` → `list`
- style: `legacy`

### GetPermissions
- `GET /api/organizations/{org_uuid}/projects/{project_uuid}/permissions` → `ProjectPermissions`
- style: `legacy`

### GetProject
- `GET /api/organizations/{org_uuid}/projects/{project_uuid}` → `Project`
- style: `legacy`

### GetProjectConversations
- `GET /api/organizations/{org_uuid}/projects/{project_uuid}/conversations_v2` → `PaginatedResponse`
- style: `legacy`

### ListDocs
- `GET /api/organizations/{org_uuid}/projects/{project_uuid}/docs` → `list`
- style: `legacy`

### ListFiles
- `GET /api/organizations/{org_uuid}/projects/{project_uuid}/files` → `list`
- style: `legacy`

### ListProjects
- `GET /api/organizations/{org_uuid}/projects_v2` → `PaginatedResponse`
- style: `legacy`

### SyncProject
- `POST /api/organizations/{org_uuid}/projects/{project_uuid}/sync` → `NoneType`
- style: `legacy`

### UpdateProject
- `PUT /api/organizations/{org_uuid}/projects/{project_uuid}` → `NoneType`
- style: `legacy`

## sync

### GetSyncAuthStatus
- `GET /api/organizations/{org_uuid}/sync/{provider}/auth` → `SyncAuth`
- style: `legacy`

### GetSyncSettings
- `GET /api/organizations/{org_uuid}/sync/settings` → `SyncSettings`
- style: `legacy`
