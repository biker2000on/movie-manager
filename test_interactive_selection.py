import pytest
from unittest.mock import patch, MagicMock
from radarr_horror_filter import interactive_keep_selection
from keep_list import KeepListManager


class TestInteractiveKeepSelection:

    def test_empty_movies_returns_empty(self):
        """Empty movie list returns empty without calling questionary."""
        keep_list = MagicMock(spec=KeepListManager)
        result = interactive_keep_selection([], keep_list)
        assert result == []

    @patch("radarr_horror_filter.questionary")
    def test_user_cancels_returns_empty(self, mock_questionary):
        """User pressing Ctrl+C returns empty list."""
        mock_questionary.checkbox.return_value.ask.return_value = None
        keep_list = MagicMock(spec=KeepListManager)
        keep_list.is_kept.return_value = False

        movies = [{'id': 1, 'title': 'Test', 'year': 2024}]
        result = interactive_keep_selection(movies, keep_list)
        assert result == []

    @patch("radarr_horror_filter.questionary")
    def test_filters_already_kept(self, mock_questionary):
        """Movies already in keep list are filtered from results."""
        movie1 = {'id': 1, 'title': 'New Movie', 'year': 2024}
        movie2 = {'id': 2, 'title': 'Already Kept', 'year': 2023}

        mock_questionary.checkbox.return_value.ask.return_value = [movie1, movie2]

        keep_list = MagicMock(spec=KeepListManager)
        keep_list.is_kept.side_effect = lambda id: id == 2

        result = interactive_keep_selection([movie1, movie2], keep_list)
        assert result == [movie1]  # movie2 filtered out

    @patch("radarr_horror_filter.questionary")
    def test_returns_selected_movies(self, mock_questionary):
        """Selected movies are returned correctly."""
        movie = {'id': 1, 'title': 'Test Movie', 'year': 2024}
        mock_questionary.checkbox.return_value.ask.return_value = [movie]

        keep_list = MagicMock(spec=KeepListManager)
        keep_list.is_kept.return_value = False

        result = interactive_keep_selection([movie], keep_list)
        assert result == [movie]

    @patch("radarr_horror_filter.QUESTIONARY_AVAILABLE", False)
    def test_raises_when_questionary_not_installed(self):
        """RuntimeError raised when questionary is not available."""
        keep_list = MagicMock(spec=KeepListManager)
        movies = [{'id': 1, 'title': 'Test', 'year': 2024}]

        with pytest.raises(RuntimeError) as exc_info:
            interactive_keep_selection(movies, keep_list)

        assert "questionary" in str(exc_info.value).lower()
        assert "pip install" in str(exc_info.value)

    @patch("radarr_horror_filter.questionary")
    def test_checkbox_called_with_correct_choices(self, mock_questionary):
        """Verify questionary.checkbox is called with proper Choice objects."""
        movie = {'id': 1, 'title': 'Test Movie', 'year': 2024}
        mock_questionary.checkbox.return_value.ask.return_value = []

        keep_list = MagicMock(spec=KeepListManager)
        keep_list.is_kept.return_value = False

        interactive_keep_selection([movie], keep_list)

        # Verify checkbox was called
        mock_questionary.checkbox.assert_called_once()

        # Verify choices were constructed correctly
        call_args = mock_questionary.checkbox.call_args
        choices = call_args.kwargs.get('choices') or call_args.args[1]
        assert len(choices) == 1
