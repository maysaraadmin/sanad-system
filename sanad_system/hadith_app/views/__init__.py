from .hadith_views import HadithListView, HadithDetailView, HadithCreateView, HadithUpdateView, HadithDeleteView
from .narrator_views import NarratorListView, NarratorDetailView
from .narrator_views_additional import NarratorCreateView, NarratorUpdateView, NarratorDeleteView
from .auth_views import LoginView, LogoutView, RegisterView
from .profile_views import ProfileView, ProfileUpdateView
from .search_views import SearchView
from .set_theme import set_theme
from .sanad_views import SanadCreateView
from .error_views import custom_404_view, custom_500_view
