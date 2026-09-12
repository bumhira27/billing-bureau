from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

class Command(BaseCommand):
    help = 'Creates default RBAC groups for the system'

    def handle(self, *args, **kwargs):
        admin_group, created = Group.objects.get_or_create(name='BureauAdmin')
        user_group, created2 = Group.objects.get_or_create(name='PracticeUser')

        if created:
            self.stdout.write(self.style.SUCCESS('Successfully created group BureauAdmin'))
        if created2:
            self.stdout.write(self.style.SUCCESS('Successfully created group PracticeUser'))
            
        self.stdout.write(self.style.SUCCESS('RBAC groups setup complete.'))
