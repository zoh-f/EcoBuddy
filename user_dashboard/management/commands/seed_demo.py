from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from user_dashboard.models import Post, Profile
from user_info.models import UserInfo


class Command(BaseCommand):
    help = 'Seed the database with demo users and sample sustainability posts.'

    def handle(self, *args, **options):
        demo, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'demo@ecobuddy.local',
                'first_name': 'Eco',
                'last_name': 'Explorer',
            },
        )
        if created:
            demo.set_password('demo1234')
            demo.save()
            self.stdout.write('Created demo user (demo / demo1234)')
        else:
            self.stdout.write('Demo user already exists (demo / demo1234)')

        mod, created = User.objects.get_or_create(
            username='moderator',
            defaults={'email': 'moderator@ecobuddy.local'},
        )
        if created:
            mod.set_password('demo1234')
            mod.save()
            self.stdout.write('Created moderator user (moderator / demo1234)')
        else:
            self.stdout.write('Moderator user already exists (moderator / demo1234)')

        mod_profile, _ = Profile.objects.get_or_create(user=mod)
        mod_profile.role = Profile.MODERATOR
        mod_profile.first_time_complete = True
        mod_profile.preferred_topics = 'living,recycling,campus'
        mod_profile.save()

        demo_profile, _ = Profile.objects.get_or_create(user=demo)
        demo_profile.first_time_complete = True
        demo_profile.preferred_topics = 'living,food,transport'
        demo_profile.bio = 'Passionate about sustainable living and campus green initiatives.'
        demo_profile.save()

        UserInfo.objects.get_or_create(
            username=demo.username,
            defaults={
                'email': demo.email,
                'display_name': 'Eco Explorer',
            },
        )

        sample_posts = [
            {
                'title': 'Started composting in my dorm',
                'content': (
                    'Set up a small countertop compost bin and convinced my floor '
                    'mates to separate food scraps. Small changes add up!'
                ),
                'topic': 'living',
                'hashtags': 'composting,zerowaste',
            },
            {
                'title': 'Campus bike share saved my commute',
                'content': (
                    'Switched from driving to the campus bike share program. '
                    'Cheaper, faster during rush hour, and way better for the planet.'
                ),
                'topic': 'transport',
                'hashtags': 'bikeshare,commute',
            },
            {
                'title': 'Recycling guide for our dining hall',
                'content': (
                    'Made a quick poster explaining what goes in recycling vs trash '
                    'at the dining hall. Happy to share the template!'
                ),
                'topic': 'recycling',
                'hashtags': 'recycling,campus',
            },
        ]

        posts_created = 0
        for post_data in sample_posts:
            _, created = Post.objects.get_or_create(
                user=demo,
                title=post_data['title'],
                defaults={
                    'content': post_data['content'],
                    'topic': post_data['topic'],
                    'hashtags': post_data['hashtags'],
                    'privacy': Post.PUBLIC,
                },
            )
            if created:
                posts_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Demo data ready. Created {posts_created} new sample post(s).'
        ))
