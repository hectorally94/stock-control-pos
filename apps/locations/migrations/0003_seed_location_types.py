from django.db import migrations


DEFAULT_TYPES = [
    ('Dépôt (Warehouse)', 'warehouse'),
    ('Boutique', 'boutique'),
]


def seed_types(apps, schema_editor):
    Enterprise = apps.get_model('core', 'Enterprise')
    LocationType = apps.get_model('locations', 'LocationType')
    Location = apps.get_model('locations', 'Location')

    for enterprise in Enterprise.objects.all():
        by_behaviour = {}
        for name, behaviour in DEFAULT_TYPES:
            lt, _ = LocationType.objects.get_or_create(
                enterprise=enterprise,
                name=name,
                defaults={'behaviour': behaviour, 'is_active': True},
            )
            by_behaviour[behaviour] = lt

        # Backfill existing locations -> point to the matching default type.
        for location in Location.objects.filter(enterprise=enterprise, type_ref__isnull=True):
            lt = by_behaviour.get(location.location_type)
            if lt:
                location.type_ref = lt
                location.save(update_fields=['type_ref'])


def unseed_types(apps, schema_editor):
    LocationType = apps.get_model('locations', 'LocationType')
    LocationType.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0002_alter_location_location_type_locationtype_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_types, unseed_types),
    ]
