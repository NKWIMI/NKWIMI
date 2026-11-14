from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from registration.models import User  # or whatever your profile model is called

class Command(BaseCommand):
    help = 'Create missing user profiles'

    def handle(self, *args, **options):
        User = get_user_model()
        
        self.stdout.write("👥 Creating missing user profiles...")
        
        created_count = 0
        for user in User.objects.all():
            # Check if user has a profile
            if not hasattr(user, 'profile'):
                self.stdout.write(f"⚠️ User {user.username} has no profile")
                
                # Try to create profile - adjust based on your actual profile model
                try:
                    # Method 1: If you have a UserProfile model with OneToOne field
                    from registration.models import UserProfile
                    profile = UserProfile.objects.create(user=user)
                    self.stdout.write(f"✅ Created profile for {user.username}")
                    created_count += 1
                except Exception as e:
                    self.stdout.write(f"❌ Could not create profile for {user.username}: {e}")
                    
                    # Method 2: If profile is created via signal or other method
                    try:
                        # Try to access profile to trigger creation
                        _ = user.profile
                        self.stdout.write(f"✅ Profile accessed/created for {user.username}")
                        created_count += 1
                    except Exception as e2:
                        self.stdout.write(f"❌ Could not access profile for {user.username}: {e2}")
        
        self.stdout.write(self.style.SUCCESS(f"🎉 Created/accessed {created_count} user profiles"))