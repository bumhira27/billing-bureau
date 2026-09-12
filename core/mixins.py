class CreatedByMixin:
    """
    A view mixin that automatically sets the created_by field
    to the current logged-in user on form valid, for CreateView subclasses.
    """
    def form_valid(self, form):
        if self.request.user.is_authenticated:
            form.instance.created_by = self.request.user
        return super().form_valid(form)
