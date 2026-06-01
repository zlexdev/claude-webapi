"""Unit tests for BaseMethod envelope (path substitution, parse_response) and method-level fixes."""

from claude_ai.methods.conversation.create_conversation import (
    CreateConversation,
    CreateConversationParams,
)
from claude_ai.methods.conversation.generate_title import (
    GenerateTitle,
    GenerateTitleParams,
)
from claude_ai.methods.organization.get_styles import GetStyles, GetStylesParams


class TestCreateConversationEnvelope:
    def test_path_substituted(self) -> None:
        method = CreateConversation()
        req = method.build_request(
            "https://claude.ai",
            CreateConversationParams(org_uuid="ORG", uuid="CONV"),
        )
        assert req.url == "https://claude.ai/api/organizations/ORG/chat_conversations"

    def test_body_carries_uuid_and_model(self) -> None:
        method = CreateConversation()
        req = method.build_request(
            "https://claude.ai",
            CreateConversationParams(
                org_uuid="o", uuid="c", name="hi", model="claude-opus-4-7"
            ),
        )
        assert req.body == {
            "uuid": "c",
            "name": "hi",
            "model": "claude-opus-4-7",
            "include_conversation_preferences": True,
            "is_temporary": False,
        }


class TestGenerateTitleEnvelope:
    def test_includes_required_message_content(self) -> None:
        method = GenerateTitle()
        req = method.build_request(
            "https://claude.ai",
            GenerateTitleParams(org_uuid="o", conv_uuid="c", message_content="hi"),
        )
        assert req.body == {"message_content": "hi", "recent_titles": []}

    def test_recent_titles_forwarded(self) -> None:
        method = GenerateTitle()
        req = method.build_request(
            "https://claude.ai",
            GenerateTitleParams(
                org_uuid="o", conv_uuid="c", message_content="m", recent_titles=["t1"]
            ),
        )
        assert req.body == {"message_content": "m", "recent_titles": ["t1"]}

    def test_parse_response_picks_title_field(self) -> None:
        assert GenerateTitle().parse_response({"title": "the title"}) == "the title"


class TestGetStylesParse:
    def test_unwraps_envelope_with_default_and_custom(self) -> None:
        data = {
            "defaultStyles": [
                {"key": "Default", "name": "Normal", "type": "default"},
                {"key": "Learning", "name": "Learning", "type": "default"},
            ],
            "customStyles": [
                {"uuid": "custom-1", "name": "Mine", "type": "custom"},
            ],
            "inlineNotice": "",
        }
        styles = GetStyles().parse_response(data)
        assert [s.name for s in styles] == ["Normal", "Learning", "Mine"]
        assert styles[0].uuid == "Default"
        assert styles[2].uuid == "custom-1"

    def test_handles_missing_keys(self) -> None:
        styles = GetStyles().parse_response({})
        assert styles == []

    def test_handles_bare_list(self) -> None:
        styles = GetStyles().parse_response(
            [{"uuid": "u", "name": "n"}],
        )
        assert len(styles) == 1
        assert styles[0].uuid == "u"


class TestGetStylesParamsEnvelope:
    def test_path_substituted(self) -> None:
        req = GetStyles().build_request(
            "https://claude.ai", GetStylesParams(org_uuid="ORG")
        )
        assert req.url == "https://claude.ai/api/organizations/ORG/list_styles"
