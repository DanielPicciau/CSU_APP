from django.db import migrations
import core.fields


def encrypt_daily_notes(apps, schema_editor):
    DailyEntry = apps.get_model("tracking", "DailyEntry")
    for entry in DailyEntry.objects.exclude(notes="").iterator():
        entry.save(update_fields=["notes"])


class Migration(migrations.Migration):

    dependencies = [
        ("tracking", "0002_add_qol_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dailyentry",
            name="notes",
            field=core.fields.EncryptedTextField(blank=True, default="", help_text="Optional notes about the day"),
        ),
        migrations.RunPython(encrypt_daily_notes, migrations.RunPython.noop),
    ]
