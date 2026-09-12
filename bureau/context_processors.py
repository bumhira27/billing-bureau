from .models import BureauProfile

def bureau_profile(request):
    """
    Returns the first BureauProfile to be available in all templates.
    """
    profile = BureauProfile.objects.first()
    return {'bureau_profile': profile}
