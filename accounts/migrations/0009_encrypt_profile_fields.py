from django.db import migrations
import core.fields


def encrypt_profile_fields(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    for profile in Profile.objects.all().iterator():
        profile.save(update_fields=[
            "display_name",
            "date_of_birth",
            "gender",
            "csu_diagnosis",
            "has_prescribed_medication",
        ])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_change_default_timezone_to_london"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="display_name",
            field=core.fields.EncryptedCharField(blank=True, default="", help_text="Optional name for personalization", max_length=100),
        ),
        migrations.AlterField(
            model_name="profile",
            name="date_of_birth",
            field=core.fields.EncryptedDateField(blank=True, help_text="User's date of birth", null=True),
        ),
        migrations.AlterField(
            model_name="profile",
            name="gender",
            field=core.fields.EncryptedCharField(blank=True, choices=[("male", "Male"), ("female", "Female"), ("non_binary", "Non-binary"), ("prefer_not_to_say", "Prefer not to say")], default="", help_text="How user describes their gender", max_length=20),
        ),
        migrations.AlterField(
            model_name="profile",
            name="csu_diagnosis",
            field=core.fields.EncryptedCharField(blank=True, choices=[("yes", "Yes"), ("no", "No"), ("unsure", "Unsure")], default="", help_text="Whether user has been diagnosed with CSU", max_length=10),
        ),
        migrations.AlterField(
            model_name="profile",
            name="has_prescribed_medication",
            field=core.fields.EncryptedCharField(blank=True, choices=[("yes", "Yes"), ("no", "No"), ("prefer_not_to_say", "Prefer not to say")], default="", help_text="Whether user has been prescribed medication for their condition", max_length=20),
        ),
        migrations.RunPython(encrypt_profile_fields, migrations.RunPython.noop),
    ]
