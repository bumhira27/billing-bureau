class CreatedByMixin:
    """
    A view mixin that automatically sets the created_by field
    to the current logged-in user on form valid, for CreateView subclasses.
    """
    def form_valid(self, form):
        if self.request.user.is_authenticated:
            form.instance.created_by = self.request.user
        return super().form_valid(form)

class RBACQuerySetMixin:
    """
    Filters the base queryset so PracticeUsers only see their assigned data.
    BureauAdmins and superusers see everything.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if user.is_superuser or user.groups.filter(name='BureauAdmin').exists():
            return qs
            
        # Determine how to filter based on the model
        model_name = self.model.__name__
        
        if model_name == 'Practice':
            return qs.filter(users=user)
        elif model_name in ['Patient', 'Claim', 'BureauInvoice', 'PatientStatement', 'RpaSubmissionLog']:
            # All these models have a direct or indirect relation to 'practice'
            if hasattr(self.model, 'practice'):
                return qs.filter(practice__users=user)
            elif model_name == 'RpaSubmissionLog':
                return qs.filter(claim__practice__users=user)
            
        return qs.none() # Default deny if model not recognized
