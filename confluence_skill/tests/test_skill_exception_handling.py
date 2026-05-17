"""Tests for ConfluenceSkill exception handling and error cases."""

from unittest.mock import MagicMock, patch

from confluence_skill.models import SkillConfig
from confluence_skill.skill import ConfluenceSkill


class TestDocumentExceptionHandling:
    """Test exception handling in document method."""

    def test_document_handles_validation_exception(self):
        """Test that document handles validation exceptions."""
        config = MagicMock(spec=SkillConfig)
        config.validate_required_fields.return_value = []
        config.confluence = MagicMock(instance_url="https://test.atlassian.net")
        config.code_analysis = MagicMock()
        config.guardrails = MagicMock(require_approval=False, dry_run_by_default=True)
        config.output = MagicMock(create_audit_trail=False, verbose=False)
        config.jira = MagicMock(enabled=False)

        with patch("confluence_skill.skill.ConfluenceClient"):
            with patch("confluence_skill.skill.CodeScanner") as mock_scanner_class:
                with patch("confluence_skill.skill.GuardailValidator") as mock_validator_class:
                    with patch("confluence_skill.skill.ApprovalGate"):
                        mock_scanner = MagicMock()
                        mock_scanner_class.return_value = mock_scanner
                        mock_scanner.scan_repos.return_value = {"apis": []}

                        mock_validator = MagicMock()
                        mock_validator_class.return_value = mock_validator
                        mock_validator.validate_metadata.side_effect = ValueError("Invalid metadata")

                        skill = ConfluenceSkill(config)
                        result = skill.document(task="Test doc", repo_path=".", dry_run=True)

                        assert not result.success
                        assert result.errors
                        assert result.duration_seconds >= 0

    def test_document_exception_includes_duration(self):
        """Test that exceptions include duration_seconds in result."""
        config = MagicMock(spec=SkillConfig)
        config.validate_required_fields.return_value = []
        config.confluence = MagicMock()
        config.code_analysis = MagicMock()
        config.guardrails = MagicMock(require_approval=False, dry_run_by_default=True)
        config.output = MagicMock(create_audit_trail=False)
        config.jira = MagicMock(enabled=False)

        with patch("confluence_skill.skill.ConfluenceClient") as mock_client_class:
            with patch("confluence_skill.skill.CodeScanner") as mock_scanner_class:
                with patch("confluence_skill.skill.GuardailValidator"):
                    with patch("confluence_skill.skill.ApprovalGate"):
                        mock_client = MagicMock()
                        mock_client_class.return_value = mock_client

                        mock_scanner = MagicMock()
                        mock_scanner_class.return_value = mock_scanner
                        mock_scanner.scan_repos.side_effect = Exception("Unexpected error")

                        skill = ConfluenceSkill(config)
                        result = skill.document(task="Test doc", dry_run=True)

                        assert result.duration_seconds is not None
                        assert result.duration_seconds >= 0


class TestGenerateMetadataEdgeCases:
    """Test _generate_metadata method edge cases."""

    def test_generate_metadata_with_minimal_config(self):
        """Test metadata generation with minimal configuration."""
        config = MagicMock(spec=SkillConfig)
        config.validate_required_fields.return_value = []
        config.confluence = MagicMock()
        config.code_analysis = MagicMock()
        config.guardrails = MagicMock()

        with patch("confluence_skill.skill.ConfluenceClient"):
            with patch("confluence_skill.skill.CodeScanner"):
                with patch("confluence_skill.skill.GuardailValidator"):
                    with patch("confluence_skill.skill.ApprovalGate"):
                        doc_config = MagicMock()
                        doc_config.metadata = MagicMock(owner="team", audience=["engineers"], labels=[])

                        skill = ConfluenceSkill(config)
                        metadata = skill._generate_metadata("Test Documentation", doc_config)

                        assert metadata.title == "Test Documentation"
                        assert metadata.owner == "team"
                        assert "engineers" in metadata.audience
                        assert isinstance(metadata.labels, list)


class TestPrintResultSummary:
    """Test _print_result_summary method."""

    def test_print_result_summary_success(self, capsys):
        """Test printing successful result summary."""
        from confluence_skill.models import DocumentGenerationResult

        config = MagicMock(spec=SkillConfig)
        config.validate_required_fields.return_value = []
        config.confluence = MagicMock()
        config.code_analysis = MagicMock()
        config.guardrails = MagicMock()

        with patch("confluence_skill.skill.ConfluenceClient"):
            with patch("confluence_skill.skill.CodeScanner"):
                with patch("confluence_skill.skill.GuardailValidator"):
                    with patch("confluence_skill.skill.ApprovalGate"):
                        result = DocumentGenerationResult(
                            success=True,
                            title="Test Doc",
                            document_id="doc-123",
                            duration_seconds=1.5,
                        )

                        skill = ConfluenceSkill(config)
                        skill._print_result_summary(result)

                        captured = capsys.readouterr()
                        # Should print something about success
                        assert len(captured.out) > 0 or len(captured.err) > 0

    def test_print_result_summary_failure(self, capsys):
        """Test printing failed result summary."""
        from confluence_skill.models import DocumentGenerationResult, ValidationError

        config = MagicMock(spec=SkillConfig)
        config.validate_required_fields.return_value = []
        config.confluence = MagicMock()
        config.code_analysis = MagicMock()
        config.guardrails = MagicMock()

        with patch("confluence_skill.skill.ConfluenceClient"):
            with patch("confluence_skill.skill.CodeScanner"):
                with patch("confluence_skill.skill.GuardailValidator"):
                    with patch("confluence_skill.skill.ApprovalGate"):
                        result = DocumentGenerationResult(
                            success=False,
                            errors=[ValidationError(level="error", field="space", message="Space not found")],
                            duration_seconds=0.5,
                        )

                        skill = ConfluenceSkill(config)
                        skill._print_result_summary(result)

                        captured = capsys.readouterr()
                        # Should print something about failure
                        assert len(captured.out) > 0 or len(captured.err) > 0
