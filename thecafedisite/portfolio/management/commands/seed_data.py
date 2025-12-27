from django.core.management.base import BaseCommand
from portfolio.models import CareerEntry, Skill
from datetime import date


class Command(BaseCommand):
    help = 'Seeds the database with sample data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Clear existing data
        CareerEntry.objects.all().delete()
        Skill.objects.all().delete()

        # Create Career Entries
        career_entries = [
            {
                'title': 'Senior Software Engineer',
                'company': 'Tech Corp',
                'location': 'San Francisco, CA',
                'start_date': date(2022, 6, 1),
                'end_date': None,
                'bullet_1': 'Led development of microservices architecture serving 10M+ daily requests',
                'bullet_2': 'Mentored team of 5 junior developers and conducted code reviews',
                'bullet_3': 'Implemented CI/CD pipelines reducing deployment time by 60%',
                'order': 0,
            },
            {
                'title': 'Software Engineer',
                'company': 'StartUp Inc',
                'location': 'Austin, TX',
                'start_date': date(2020, 3, 1),
                'end_date': date(2022, 5, 31),
                'bullet_1': 'Built full-stack web applications using Django and React',
                'bullet_2': 'Designed and implemented RESTful APIs for mobile applications',
                'bullet_3': 'Optimized database queries improving application performance by 40%',
                'order': 1,
            },
            {
                'title': 'Junior Developer',
                'company': 'Digital Agency',
                'location': 'Remote',
                'start_date': date(2018, 9, 1),
                'end_date': date(2020, 2, 28),
                'bullet_1': 'Developed responsive web interfaces using HTML, CSS, and JavaScript',
                'bullet_2': 'Collaborated with design team to implement pixel-perfect UI components',
                'bullet_3': 'Maintained and updated client websites ensuring 99.9% uptime',
                'order': 2,
            },
        ]

        for entry in career_entries:
            CareerEntry.objects.create(**entry)
        self.stdout.write(self.style.SUCCESS(f'Created {len(career_entries)} career entries'))

        # Create Skills
        skills = [
            # Technologies and Frameworks
            {'name': 'Django', 'category': 'tech_frameworks', 'proficiency': 5, 'order': 0},
            {'name': 'React', 'category': 'tech_frameworks', 'proficiency': 4, 'order': 1},
            {'name': 'Node.js', 'category': 'tech_frameworks', 'proficiency': 4, 'order': 2},
            {'name': 'Tailwind CSS', 'category': 'tech_frameworks', 'proficiency': 5, 'order': 3},
            {'name': 'AWS', 'category': 'tech_frameworks', 'proficiency': 3, 'order': 4},

            # Programming Languages
            {'name': 'Python', 'category': 'programming_languages', 'proficiency': 5, 'order': 0},
            {'name': 'JavaScript', 'category': 'programming_languages', 'proficiency': 4, 'order': 1},
            {'name': 'TypeScript', 'category': 'programming_languages', 'proficiency': 4, 'order': 2},
            {'name': 'SQL', 'category': 'programming_languages', 'proficiency': 4, 'order': 3},

            # Databases
            {'name': 'PostgreSQL', 'category': 'databases', 'proficiency': 4, 'order': 0},
            {'name': 'MongoDB', 'category': 'databases', 'proficiency': 3, 'order': 1},
            {'name': 'Redis', 'category': 'databases', 'proficiency': 3, 'order': 2},

            # Developer Tools
            {'name': 'Git', 'category': 'developer_tools', 'proficiency': 5, 'order': 0},
            {'name': 'Docker', 'category': 'developer_tools', 'proficiency': 4, 'order': 1},
            {'name': 'VS Code', 'category': 'developer_tools', 'proficiency': 5, 'order': 2},
            {'name': 'Linux', 'category': 'developer_tools', 'proficiency': 4, 'order': 3},
        ]

        for skill in skills:
            Skill.objects.create(**skill)
        self.stdout.write(self.style.SUCCESS(f'Created {len(skills)} skills'))

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
